# -*- coding: utf-8 -*-
# Игровое кресло Юрчика — по фото: зелёно-чёрное «гоночное» кресло из кожзама.
#   * высокая спинка: чёрная середина, по бокам — зелёные валики-«крылья» до самых «плеч»;
#     на середине — зелёные шевроны, внизу — горизонтальная простёжка, вверху — вышитая эмблема и прорези под ремни;
#   * сиденье «ковшом»: чёрная середина с перфорированной вставкой и зелёной окантовкой, зелёные валики по бокам;
#   * чёрные подлокотники на стойках, механизм качания, газлифт в кожухе, пятилучевая крестовина, сдвоенные колёсики.
#
# Запуск (Blender 5.2, из корня проекта):
#   blender -b --factory-startup --python tools/blender/build_gaming_chair.py
# или через Blender MCP: exec(open(r"<путь>\tools\blender\build_gaming_chair.py", encoding="utf-8").read())
#   (скрипт строит всё в своей сцене GamingChair и не трогает остальные сцены).
# Результат: assets/textures/gc_*.png, assets/models/gaming_chair.gltf
#   GamingChair_nocol — само кресло (без коллизии, ps2_import.gd пропускает «nocol»),
#   GamingChairCol-colonly — простые ящики, из которых Godot делает только коллизию.
#
# Начало координат — пол под газлифтом, кресло смотрит вдоль +Y (в Godot — вдоль −Z).
# В stairwell.tscn стоит узлом GamingChair у компьютерного стола.
#
# Все мягкие детали — «лофты» loft(): цепочка скруглённых сечений (суперэллипс), натянутая вдоль пути,
# с заглушками на концах. Так валики, подушки и ножки получаются гладкими без модификаторов.
import bpy, bmesh, os, sys, math
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else r"C:\Users\mrs\Documents\yuranchik_game\tools\blender"
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from tex_lib import save
from ps2_hero import C, finish
from ps2_style import noise

_ns = {"NO_MAIN": True}
exec(compile(open(os.path.join(HERE, "build_yard.py"), encoding="utf-8").read(), "build_yard.py", "exec"), _ns)
mat = _ns["mat"]
OUT = os.path.join(ROOT, "assets", "models")
R = np.random.default_rng(2011)

# --- размеры (м) ---
SEAT_Z = 0.465                 # середина подушки сиденья; верх ~0.52, валики ~0.57
HINGE = Vector((0.0, -0.235, 0.47))   # нижний край спинки
TILT = 12.0                    # наклон спинки назад, градусы
BACK_H = 0.90                  # высота спинки вдоль наклона
BACK_U = 0.30                  # полуширина, на которую растянута текстура спинки
SEAT_U, SEAT_Y0, SEAT_Y1 = 0.20, -0.26, 0.28   # область текстуры сиденья


# =====================================================================================
#  Текстуры
# =====================================================================================
def leather(w, h, col, amp=0.22, crease=0.18):
    """Кожзам: неровный тон, мелкое зерно, светлые заломы-морщинки (свет «запечён»)."""
    a = np.ones((h, w, 3), np.float32) * C(*col)
    a *= (1 - amp / 2 + amp * noise(w, h, 4, 4, R, oct=3))[..., None]
    a *= (0.93 + 0.10 * R.random((h, w)).astype(np.float32))[..., None]
    n = noise(w, h, 10, 10, R, oct=2)
    ridge = np.clip(1 - np.abs(n - 0.5) * 30, 0, 1)                 # тонкие линии по изолиниям шума — заломы
    a *= (1 + crease * ridge)[..., None]
    return a


def tex_black():
    save("gc_black", finish(leather(128, 128, (0.060, 0.060, 0.066)), 1.0, crisp=0.3))


def tex_green():
    a = leather(128, 128, (0.055, 0.30, 0.12), amp=0.22, crease=0.35)
    save("gc_green", finish(a, 1.0, crisp=0.3))


def tex_plastic():
    a = np.ones((64, 64, 3), np.float32) * C(0.045, 0.045, 0.05)
    a *= (0.85 + 0.3 * noise(64, 64, 4, 4, R, oct=2))[..., None]
    a *= (0.95 + 0.08 * R.random((64, 64)).astype(np.float32))[..., None]
    save("gc_plastic", finish(a, 1.0, crisp=0.2))


def _uv_grid(w, h, umin, umax, vmin, vmax):
    """Координаты пикселей в метрах детали: x — поперёк, v — вдоль (снизу вверх)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    x = umin + (xx + 0.5) / w * (umax - umin)
    v = vmax - (yy + 0.5) / h * (vmax - vmin)
    return x, v


def _stroke(a, mask, col, k=1.0):
    a[mask] = a[mask] * (1 - k) + np.array(C(*col), np.float32) * k


def tex_back():
    """Середина спинки: u — поперёк (−BACK_U..BACK_U), v — вдоль спинки (0 — низ, 1 — верх, BACK_H)."""
    w, h = 128, 256
    a = leather(w, h, (0.058, 0.058, 0.064))
    x, v = _uv_grid(w, h, -BACK_U, BACK_U, 0.0, BACK_H)
    ax = np.abs(x)
    # нижняя часть — горизонтальная простёжка «подушками»: светлый край сверху, тёмный шов снизу
    low = (v > 0.04) & (v < 0.36) & (ax < 0.16)
    ph = np.mod(v - 0.04, 0.064) / 0.064
    a[low] *= (0.80 + 0.45 * np.sin(ph[low] * math.pi) ** 0.6)[..., None]
    _stroke(a, low & (ph < 0.06), (0.02, 0.02, 0.02), 0.9)
    # зелёная окантовка середины (кант)
    pipe = (np.abs(ax - 0.165) < 0.006) & (v > 0.04) & (v < 0.66)
    _stroke(a, pipe, (0.08, 0.40, 0.17), 0.95)
    # шевроны: три зелёных «галочки» остриём вниз
    for k, v0 in enumerate((0.42, 0.50, 0.58)):
        line = v0 + ax * 0.55
        m = (np.abs(v - line) < 0.016) & (ax < 0.155)
        _stroke(a, m, (0.08, 0.42, 0.18), 0.95)
        _stroke(a, (np.abs(v - line + 0.019) < 0.003) & (ax < 0.155), (0.15, 0.55, 0.26), 0.5)    # блик по краю
    # прорези под ремни
    for sx in (-0.095, 0.095):
        m = (((x - sx) / 0.018) ** 4 + ((v - 0.735) / 0.032) ** 4) < 1
        _stroke(a, m, (0.0, 0.0, 0.0), 1.0)
        rim = ((((x - sx) / 0.024) ** 4 + ((v - 0.735) / 0.039) ** 4) < 1) & ~m
        _stroke(a, rim, (0.12, 0.12, 0.13), 0.7)
    # вышитая эмблема вверху: щиток и две строчки «надписи» под ним (своя, без марки)
    sh = (np.abs(x) / 0.045 + np.clip((0.865 - v) / 0.05, 0, 9) ** 1.5 < 1) & (v < 0.865) & (v > 0.81)
    _stroke(a, sh, (0.72, 0.74, 0.72), 0.85)
    _stroke(a, sh & (np.abs(x) < 0.006), (0.08, 0.40, 0.17), 0.9)
    for vv, ww in ((0.798, 0.075), (0.786, 0.05)):
        m = (np.abs(v - vv) < 0.004) & (np.abs(x) < ww) & (np.mod(x * 160, 1.0) < 0.7)
        _stroke(a, m, (0.65, 0.67, 0.65), 0.8)
    # грязь: засаленное место под головой и затёртости у края
    g = np.exp(-((x / 0.12) ** 2 + ((v - 0.70) / 0.06) ** 2))
    a *= (1 + 0.25 * g)[..., None]
    save("gc_back", finish(a, 1.0, crisp=0.35))


def tex_seat():
    """Середина сиденья: u — поперёк (−SEAT_U..SEAT_U), v — от задней кромки к передней."""
    w, h = 128, 128
    a = leather(w, h, (0.055, 0.055, 0.060), crease=0.28)
    x, v = _uv_grid(w, h, -SEAT_U, SEAT_U, SEAT_Y0, SEAT_Y1)
    ax = np.abs(x)
    ins = (ax < 0.115) & (v > -0.20) & (v < 0.22)
    a[ins] *= 0.85
    dots = ins & (np.mod(x * 90, 1) < 0.35) & (np.mod(v * 90, 1) < 0.35)               # перфорация
    a[dots] *= 0.45
    for e in (0.12,):
        _stroke(a, (np.abs(ax - e) < 0.006) & (v > -0.21) & (v < 0.23), (0.08, 0.40, 0.17), 0.95)
    _stroke(a, (np.abs(v - 0.225) < 0.005) & (ax < 0.125), (0.08, 0.40, 0.17), 0.95)
    # протёрто посередине: светлее и залоснилось
    g = np.exp(-((x / 0.10) ** 2 + ((v - 0.02) / 0.12) ** 2))
    a *= (1 + 0.35 * g)[..., None]
    save("gc_seat", finish(a, 1.0, crisp=0.35))


# =====================================================================================
#  Геометрия
# =====================================================================================
class Mesh:
    def __init__(self):
        self.v, self.f, self.uv, self.mi, self.mats = [], [], [], [], []

    def _m(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def poly(self, pts, uvs, m):
        base = len(self.v)
        self.v += [tuple(p) for p in pts]
        self.f.append(tuple(range(base, base + len(pts))))
        self.uv.append(list(uvs))
        self.mi.append(self._m(m))

    def build(self, name, coll, smooth=True, sharp=50.0):
        me = bpy.data.meshes.get(name)
        if me and me.users == 0:
            bpy.data.meshes.remove(me)
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        uvl = me.uv_layers.new(name="UVMap")
        k = 0
        for poly, uvs in zip(me.polygons, self.uv):
            for li, uv in zip(poly.loop_indices, uvs):
                uvl.data[li].uv = uv
        for m in self.mats:
            me.materials.append(m)
        for poly, mi in zip(me.polygons, self.mi):
            poly.material_index = mi
            poly.use_smooth = smooth
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me); bm.free()
        if smooth:
            me.set_sharp_from_angle(angle=math.radians(sharp))
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        return ob


def ring(n, a, b, segs):
    """Сечение-суперэллипс: n = 2 — эллипс, 4 — скруглённый прямоугольник, 8 — почти прямоугольник."""
    out = []
    for i in range(segs):
        t = 2 * math.pi * i / segs
        c, s = math.cos(t), math.sin(t)
        out.append((a * math.copysign(abs(c) ** (2 / n), c), b * math.copysign(abs(s) ** (2 / n), s)))
    return out


def loft(mb, secs, m, uv="tile", xf=Matrix.Identity(4), segs=16, caps=(True, True), tile=0.32):
    """secs: [(центр, ось_X, ось_Y, a, b, n)] — сечения вдоль пути (оси — единичные векторы в плоскости сечения).
    uv: "tile" — развёртка по периметру и длине в метрах (текстура повторяется), или функция f(точка) -> (u, v)
    от точки до преобразования xf (плоская проекция для уникальных текстур)."""
    rings, per = [], []
    for (c, X, Y, a, b, n) in secs:
        c, X, Y = Vector(c), Vector(X), Vector(Y)
        pts = [c + X * px + Y * py for (px, py) in ring(n, a, b, segs)]
        rings.append(pts)
        L = sum((pts[(i + 1) % segs] - pts[i]).length for i in range(segs))
        per.append(L)
    dist = [0.0]
    for k in range(1, len(secs)):
        dist.append(dist[-1] + (Vector(secs[k][0]) - Vector(secs[k - 1][0])).length)
    T = lambda p: xf @ p

    def UV(k, i, p):
        if callable(uv):
            return uv(p)
        return (i / segs * per[k] / tile, dist[k] / tile)

    for k in range(len(rings) - 1):
        for i in range(segs):
            j = i + 1
            q = [rings[k][i], rings[k][j % segs], rings[k + 1][j % segs], rings[k + 1][i]]
            uvs = [UV(k, i, q[0]), UV(k, j, q[1]), UV(k + 1, j, q[2]), UV(k + 1, i, q[3])]
            mb.poly([T(p) for p in q], uvs, m)
    for end, k in ((0, 0), (1, len(rings) - 1)):
        if not caps[end]:
            continue
        c, X, Y = Vector(secs[k][0]), Vector(secs[k][1]), Vector(secs[k][2])
        pts = rings[k] if end else rings[k][::-1]
        uvs = [uv(p) if callable(uv) else ((p - c).dot(X) / tile, (p - c).dot(Y) / tile) for p in pts]
        mb.poly([T(p) for p in pts], uvs, m)


def along(axis, X, Y, pts):
    """Сечения вдоль одной оси: pts = [(позиция, смещение_по_X, смещение_по_Y, a, b, n)]."""
    return [(axis * t + X * ox + Y * oy, X, Y, a, b, n) for (t, ox, oy, a, b, n) in pts]


def lerp_tab(tab, t):
    """Линейная интерполяция по таблице [(t, значения...)]."""
    for (t0, *v0), (t1, *v1) in zip(tab, tab[1:]):
        if t0 <= t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return [a + (b - a) * f for a, b in zip(v0, v1)]
    return list(tab[-1][1:]) if t > tab[-1][0] else list(tab[0][1:])


EX, EY, EZ = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


def chair(M):
    mb = Mesh()
    BK, GR, PL, BKP, ST = M["black"], M["green"], M["plastic"], M["back"], M["seat"]

    # ---------------- спинка: строим в своих координатах (x — вбок, y — вперёд, z — вверх вдоль спинки) ----------------
    XB = Matrix.Translation(HINGE) @ Matrix.Rotation(math.radians(-TILT), 4, 'X')
    back_uv = lambda p: (p.x / (2 * BACK_U) + 0.5, p.z / BACK_H)
    # середина: v, полуширина, полутолщина, вынос вперёд (поясница выпирает)
    mid = [(0.00, 0.14, 0.02, 0.000), (0.03, 0.165, 0.045, 0.005), (0.18, 0.17, 0.052, 0.025), (0.30, 0.165, 0.058, 0.038),
           (0.44, 0.17, 0.05, 0.020), (0.58, 0.19, 0.046, 0.005), (0.68, 0.215, 0.046, 0.0), (0.80, 0.22, 0.046, 0.0),
           (0.865, 0.205, 0.042, 0.0), (0.895, 0.17, 0.03, 0.0), (0.905, 0.12, 0.012, 0.0)]
    loft(mb, [(Vector((0, y, z)), EX, EY, hw, th, 4) for (z, hw, th, y) in mid], BKP, uv=back_uv, xf=XB, segs=20)
    # зелёные «крылья»: v, x центра, y центра, a (вбок), b (вперёд)
    wing = [(0.00, 0.185, 0.020, 0.025, 0.030), (0.04, 0.198, 0.045, 0.042, 0.055), (0.18, 0.205, 0.075, 0.050, 0.075),
            (0.32, 0.205, 0.082, 0.050, 0.078), (0.46, 0.212, 0.065, 0.050, 0.068), (0.58, 0.232, 0.045, 0.046, 0.058),
            (0.68, 0.252, 0.032, 0.042, 0.052), (0.76, 0.260, 0.022, 0.038, 0.045), (0.81, 0.255, 0.012, 0.028, 0.035),
            (0.835, 0.245, 0.005, 0.012, 0.016)]
    for s in (-1, 1):
        secs = [(Vector((s * x, y, z)), EX, EY, a, b, 2.6) for (z, x, y, a, b) in wing]
        loft(mb, secs, GR, xf=XB, segs=14)
    # «плечи» и верх: чёрная подушка поверх концов крыльев
    top = [(0.80, 0.235, 0.040, 0.0), (0.83, 0.285, 0.050, 0.0), (0.87, 0.29, 0.050, 0.0), (0.90, 0.26, 0.042, 0.0),
           (0.92, 0.20, 0.025, 0.0), (0.925, 0.14, 0.01, 0.0)]
    loft(mb, [(Vector((0, -0.005 + y, z)), EX, EY, hw, th, 5) for (z, hw, th, y) in top], BK, xf=XB, segs=20)
    # задняя стенка: обтянутая чёрным «скорлупа» на всю ширину, закрывает щели сзади
    shell = [(0.00, 0.17, 0.02), (0.03, 0.225, 0.025), (0.30, 0.24, 0.025), (0.50, 0.245, 0.025), (0.62, 0.265, 0.025),
             (0.74, 0.285, 0.025), (0.86, 0.285, 0.025), (0.91, 0.22, 0.02), (0.925, 0.15, 0.01)]
    loft(mb, [(Vector((0, -0.045, z)), EX, EY, hw, th, 6) for (z, hw, th) in shell], BK, xf=XB, segs=20)
    # кронштейн спинки: две чёрные пластины от сиденья к задней стенке
    for s in (-1, 1):
        p0 = Vector((s * 0.20, -0.20, SEAT_Z - 0.06)); p1 = XB @ Vector((s * 0.20, -0.07, 0.10))
        d = (p1 - p0).normalized()
        loft(mb, [(p0, EX, d.cross(EX).normalized(), 0.012, 0.03, 6), (p1, EX, d.cross(EX).normalized(), 0.012, 0.03, 6)], PL, segs=10)

    # ---------------- сиденье ----------------
    seat_uv = lambda p: (p.x / (2 * SEAT_U) + 0.5, (p.y - SEAT_Y0) / (SEAT_Y1 - SEAT_Y0))
    # середина: y, z центра, полуширина, полутолщина (передняя кромка — валиком вниз)
    sc = [(-0.245, 0.465, 0.15, 0.025), (-0.225, 0.465, 0.185, 0.045), (-0.12, 0.462, 0.19, 0.052), (0.04, 0.462, 0.19, 0.054),
          (0.17, 0.468, 0.19, 0.052), (0.235, 0.462, 0.185, 0.045), (0.262, 0.448, 0.17, 0.03), (0.272, 0.44, 0.13, 0.012)]
    loft(mb, [(Vector((0, y, z)), EX, EZ, hw, th, 4) for (y, z, hw, th) in sc], ST, uv=seat_uv, segs=20)
    # зелёные валики по бокам: y, x центра, z центра, a, b
    sb = [(-0.25, 0.215, 0.495, 0.02, 0.025), (-0.23, 0.222, 0.505, 0.042, 0.045), (-0.10, 0.228, 0.512, 0.050, 0.052),
          (0.06, 0.232, 0.520, 0.052, 0.056), (0.18, 0.232, 0.518, 0.050, 0.052), (0.245, 0.228, 0.500, 0.044, 0.044),
          (0.272, 0.222, 0.478, 0.030, 0.028), (0.282, 0.218, 0.468, 0.012, 0.012)]
    for s in (-1, 1):
        loft(mb, [(Vector((s * x, y, z)), EX, EZ, a, b, 2.6) for (y, x, z, a, b) in sb], GR, segs=14)
    # низ сиденья — чёрная обтянутая основа
    loft(mb, [(Vector((0, y, 0.42)), EX, EZ, hw, 0.022, 6) for (y, hw) in
              ((-0.25, 0.22), (-0.235, 0.265), (0.25, 0.27), (0.275, 0.24))], BK, segs=20)

    # ---------------- подлокотники ----------------
    for s in (-1, 1):
        # кронштейн под сиденьем → стойка вверх
        loft(mb, along(EX, EY, EZ, [(s * 0.10, -0.03, 0.392, 0.03, 0.008, 6), (s * 0.305, -0.03, 0.392, 0.03, 0.008, 6)]), PL, segs=10)
        loft(mb, [(Vector((s * 0.305, -0.03, 0.385)), EX, EY, 0.016, 0.032, 5), (Vector((s * 0.305, -0.03, 0.55)), EX, EY, 0.016, 0.032, 5),
                  (Vector((s * 0.305, -0.03, 0.655)), EX, EY, 0.014, 0.028, 5)], PL, segs=12)
        loft(mb, [(Vector((s * 0.305, -0.03, 0.47)), EX, EY, 0.019, 0.036, 5), (Vector((s * 0.305, -0.03, 0.60)), EX, EY, 0.019, 0.036, 5)], PL, segs=12)
        # кнопка регулировки высоты
        loft(mb, along(EX, EY, EZ, [(s * 0.32, -0.03 + 0.03, 0.60, 0.006, 0.012, 4), (s * 0.327, -0.03 + 0.03, 0.60, 0.006, 0.012, 4)]), PL, segs=8)
        # мягкая накладка
        pad = [(-0.20, 0.005, 0.010), (-0.19, 0.038, 0.018), (0.06, 0.042, 0.020), (0.085, 0.036, 0.018), (0.095, 0.01, 0.008)]
        loft(mb, [(Vector((s * 0.31, y, 0.675)), EX, EZ, a, b, 4) for (y, a, b) in pad], PL, segs=14)

    # ---------------- механизм, газлифт, крестовина ----------------
    loft(mb, along(EY, EX, EZ, [(-0.13, 0, 0.375, 0.08, 0.02, 6), (-0.12, 0, 0.375, 0.10, 0.025, 6), (0.10, 0, 0.372, 0.10, 0.025, 6),
                                (0.12, 0, 0.372, 0.075, 0.018, 6)]), PL, segs=14)
    loft(mb, along(EX, EY, EZ, [(0.09, 0.05, 0.37, 0.006, 0.006, 2), (0.30, 0.10, 0.36, 0.006, 0.006, 2)]), PL, segs=6, caps=(False, True))   # рычаг
    loft(mb, along(EX, EY, EZ, [(0.30, 0.10, 0.36, 0.012, 0.012, 2), (0.33, 0.10, 0.36, 0.012, 0.012, 2)]), PL, segs=8)
    loft(mb, along(EZ, EX, EY, [(0.255, 0, 0, 0.022, 0.022, 2), (0.365, 0, 0, 0.022, 0.022, 2)]), M["chrome"], segs=12)       # шток
    loft(mb, along(EZ, EX, EY, [(0.085, 0, 0, 0.040, 0.040, 2), (0.15, 0, 0, 0.038, 0.038, 2), (0.155, 0, 0, 0.034, 0.034, 2),
                                (0.205, 0, 0, 0.034, 0.034, 2), (0.21, 0, 0, 0.030, 0.030, 2), (0.26, 0, 0, 0.030, 0.030, 2)]), PL, segs=14)  # кожух-«гармошка»
    loft(mb, along(EZ, EX, EY, [(0.06, 0, 0, 0.05, 0.05, 2), (0.10, 0, 0, 0.058, 0.058, 2), (0.115, 0, 0, 0.045, 0.045, 2)]), PL, segs=14)  # ступица
    for k in range(5):
        r_ = math.radians(90 + k * 72)
        D = Vector((math.cos(r_), math.sin(r_), 0)); Tn = Vector((-D.y, D.x, 0))
        leg = [(0.03, 0.098, 0.032, 0.028), (0.08, 0.095, 0.030, 0.026), (0.20, 0.083, 0.024, 0.020), (0.30, 0.074, 0.019, 0.016),
               (0.325, 0.072, 0.015, 0.013), (0.335, 0.071, 0.008, 0.006)]
        loft(mb, [(D * t + EZ * z, Tn, EZ, a, b, 3) for (t, z, a, b) in leg], PL, segs=12)
        # колёсико: стакан, вилка, два колеса на общей оси
        cp = D * 0.315
        loft(mb, along(EZ, EX, EY, [(0.058, cp.x, cp.y, 0.012, 0.012, 2), (0.07, cp.x, cp.y, 0.012, 0.012, 2)]), PL, segs=8)
        ax = Vector((math.cos(r_ + 0.6), math.sin(r_ + 0.6), 0))            # колёса чуть развёрнуты — как стоят на самом деле
        fw = ax.cross(EZ).normalized()
        cw = cp + EZ * 0.03 - fw * 0.012
        loft(mb, [(cp + EZ * 0.055 - ax * 0.004, ax, EZ, 0.004, 0.014, 4), (cp + EZ * 0.055 + ax * 0.004, ax, EZ, 0.004, 0.014, 4)], PL, segs=8)
        loft(mb, [(cw - ax * 0.006, fw, EZ, 0.026, 0.026, 4), (cw + ax * 0.006, fw, EZ, 0.026, 0.026, 4)], PL, segs=8)   # колпак между колёсами
        for sg in (-1, 1):
            c0 = cw + ax * sg * 0.008
            loft(mb, [(c0, fw, EZ, 0.026, 0.026, 2), (c0 + ax * sg * 0.016, fw, EZ, 0.026, 0.026, 2)], M["wheel"], segs=12)
    return mb


def collision():
    """Коллизия: ящики сиденья, спинки (под наклоном), стойка; лучи крестовины."""
    mb = Mesh()
    m = bpy.data.materials.get("GcCol") or bpy.data.materials.new("GcCol")

    def box(c, hx, hy, hz, rot=Matrix.Identity(3)):
        c = Vector(c)
        for (ax, sgn) in ((0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1)):
            pass
        corners = [c + rot @ Vector((sx * hx, sy * hy, sz * hz)) for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)]
        for idx in ((0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)):
            mb.poly([corners[i] for i in idx], [(0, 0)] * 4, m)

    box((0, 0.01, 0.47), 0.28, 0.275, 0.075)
    rb = Matrix.Rotation(math.radians(-TILT), 3, 'X')
    box(HINGE + rb @ Vector((0, 0.0, 0.46)), 0.29, 0.07, 0.46, rb)
    box((0, 0, 0.22), 0.04, 0.04, 0.16)
    for k in range(5):
        r_ = math.radians(90 + k * 72)
        rz = Matrix.Rotation(r_, 3, 'Z')
        box(rz @ Vector((0.17, 0, 0.06)), 0.17, 0.03, 0.05, rz)
    return mb


def main():
    if bpy.context.window:
        sc = bpy.data.scenes.get("GamingChair") or bpy.data.scenes.new("GamingChair")
        bpy.context.window.scene = sc
    else:
        sc = bpy.context.scene
    for ob in list(sc.objects):
        if ob.type == 'MESH':
            bpy.data.objects.remove(ob, do_unlink=True)
    for me in [m for m in bpy.data.meshes if m.name.startswith("GamingChair") and m.users == 0]:
        bpy.data.meshes.remove(me)
    tex_black(); tex_green(); tex_plastic(); tex_back(); tex_seat()
    M = {
        "black": mat("GcLeatherBlack", "gc_black", rough=0.55), "green": mat("GcLeatherGreen", "gc_green", rough=0.55),
        "back": mat("GcBack", "gc_back", rough=0.55), "seat": mat("GcSeat", "gc_seat", rough=0.6),
        "plastic": mat("GcPlastic", "gc_plastic", rough=0.6), "wheel": mat("GcWheel", "gc_plastic", rough=0.75),
        "chrome": mat("GcChrome", "gc_plastic", rough=0.25, metal=0.9),
    }
    coll = sc.collection
    ob = chair(M).build("GamingChair_nocol", coll)
    col = collision().build("GamingChairCol-colonly", coll, smooth=False)
    bpy.context.view_layer.update()
    for o in sc.objects:
        o.select_set(o in (ob, col))
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "gaming_chair.gltf"), use_selection=True, use_active_scene=True,
                              export_keep_originals=True, export_format='GLTF_SEPARATE', export_apply=True, export_yup=True)
    return {"tris": sum(len(p.vertices) - 2 for p in ob.data.polygons), "mats": [m.name for m in ob.data.materials]}


RESULT = main()
print("BUILD_GAMING_CHAIR", RESULT)
