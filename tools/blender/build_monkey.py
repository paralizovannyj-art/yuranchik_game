# -*- coding: utf-8 -*-
# Детёныш макаки (YUR-27): low-poly модель в стиле PS2 по концепт-листу docs/references/monkey/monkey_concept_sheet.png.
# Фото-референсы деталей (мех, мордочка, кисти): docs/references/monkey/macaque_photo_*.png.
#
# Устроено так же, как Юрчик (tools/blender/build_yurchik_v3.py, помощники берутся оттуда через load()):
#   1. Геометрия — «кольца»-сечения, снятые с силуэтов трёх видов концепта (спереди / сбоку / сзади), соединённые в трубы.
#      Голова и туловище — горизонтальные кольца; лапы, кисти, стопы и хвост — кольца вдоль оси кости.
#   2. Развёртка — прямоугольные островки, упакованные в один атлас 256×256.
#   3. Текстура — проекция концепт-листа на модель + процедурная дорисовка: глаза, кисти/стопы, уши, ворс,
#      рыжина снизу, грязь и изморозь. Свет запечён в текстуру. Две полоски «бахромы» с альфой
#      (вокруг мордочки и вдоль спины) дают пушистый силуэт.
#   4. Скелет — свой, простой (таз, 2 кости позвоночника, шея, голова, лапы по 3 кости, хвост 4 кости). Поза покоя — сидя.
#   5. Анимации — процедурные ключи: Idle (3.6 с, цикл), LookAround (4 с, цикл), Eat (3 с, цикл).
#
# Масштаб. На концепт-листе справа Юрчик в полный рост: от макушки шапки y≈48 до подошвы y≈912 → 864 px.
# Сидящая обезьянка рядом с ним: от макушки y≈688 до земли y≈912 → 224 px, т.е. 224 / 864 = 0.259 роста Юрчика.
# Рост Юрчика в assets/models/yurchik.gltf (с шапкой) — 1.783 м → обезьянка сидя 0.259 × 1.783 ≈ 0.462 м.
# На трёх видах (слева) обезьянка от макушки y≈408 до земли y≈745 → 337 px → 1 px = 0.462 / 337 = 0.001372 м.
#
# Оси Blender: Z — вверх, обезьянка смотрит в −Y (в Godot это +Z), её левая сторона — +X.
# Начало координат — на земле между стопами.
#
# Запуск — через Blender MCP в открытом Blender (сцена «Monkey» создаётся заново, остальные сцены не трогаются):
#   exec(open(r"<проект>\tools\blender\build_monkey.py", encoding="utf-8").read(),
#        {"__file__": r"<проект>\tools\blender\build_monkey.py", "MONKEY_PREVIEW": r"<папка для превью>"})
# или без интерфейса:  blender -b --factory-startup --python tools/blender/build_monkey.py -- [папка для превью]
# Результат: assets/models/monkey.gltf (+ .bin), assets/textures/monkey.png.
import bpy, os, sys, math, json, importlib.util
import numpy as np
from mathutils import Vector, Matrix, Quaternion

HERE = os.path.dirname(os.path.abspath(globals().get("__file__") or __file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
_ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = globals().get("MONKEY_PREVIEW") or (_ARGS[0] if _ARGS else None)
REF_PATH = os.path.join(ROOT, "docs", "references", "monkey", "monkey_concept_sheet.png")
TEX_NAME = "monkey"
SCENE = "Monkey"
ATLAS = 256
FPS = 30


def load(name, cut):
    src = open(os.path.join(HERE, name), encoding="utf-8").read()
    ns = {"YUR_ROOT": ROOT, "__file__": os.path.join(HERE, name)}
    exec(compile(src[:src.rindex(cut)], name, "exec"), ns)
    return ns


Y = load("build_yurchik_v3.py", "\nresult = main()")
MB, loft, sellipse = Y["MB"], Y["loft"], Y["sellipse"]
vnoise, fbm, col, rad, smooth = Y["vnoise"], Y["fbm"], Y["col"], Y["rad"], Y["smooth"]
fill_invalid, erode = Y["fill_invalid"], Y["erode"]

# --- привязка концепт-листа к метрам (см. расчёт масштаба в шапке) ---
S = 0.001372
GY = 745.0                      # строка земли на трёх видах
CXF, CXS, CXB = 186.0, 500.0, 813.0   # центр вида спереди; Y = 0 на виде сбоку; центр вида сзади
SIDE_EYE = (542.0, 470.0, 14.0)       # глаз на виде сбоку (px x, y, радиус) — закрашиваем кожей вокруг
# Уши на концепте (px x, y, полуоси rx, ry). Их стираем из проекции (заливаем мехом вокруг), иначе на голове
# рисуется второе, плоское ухо рядом с настоящим 3D-ухом.
CONCEPT_EARS = [(133, 460, 13, 24), (236, 460, 13, 24),     # спереди
                (482, 463, 19, 27),                          # сбоку
                (763, 467, 13, 24), (866, 467, 13, 24)]      # сзади

# =====================================================================================
#  Скелет: (имя, голова, хвост, родитель). Правая сторона — зеркало левой.
# =====================================================================================
TAIL_PATH = [(0.0, 0.125, 0.060), (0.002, 0.160, 0.032), (0.008, 0.190, 0.017), (0.030, 0.215, 0.012),
             (0.065, 0.228, 0.011), (0.105, 0.222, 0.010), (0.142, 0.200, 0.009), (0.168, 0.168, 0.008),
             (0.180, 0.132, 0.007)]
TAIL_R = [0.017, 0.015, 0.013, 0.012, 0.011, 0.010, 0.009, 0.0085, 0.007]

LEFT_BONES = [
    ("UpperArm", (0.062, 0.025, 0.255), (0.054, -0.068, 0.158), "Spine2"),
    ("Forearm", (0.054, -0.068, 0.158), (0.048, -0.098, 0.034), "UpperArm"),
    ("Hand", (0.048, -0.098, 0.034), (0.050, -0.152, 0.005), "Forearm"),
    ("Thigh", (0.058, 0.075, 0.065), (0.115, -0.040, 0.172), "Hips"),
    ("Shin", (0.115, -0.040, 0.172), (0.105, 0.008, 0.030), "Thigh"),
    ("Foot", (0.105, 0.008, 0.030), (0.121, -0.074, 0.006), "Shin"),
]
BONES = [
    ("Hips", (0, 0.085, 0.035), (0, 0.075, 0.120), None),
    ("Spine1", (0, 0.075, 0.120), (0, 0.060, 0.200), "Hips"),
    ("Spine2", (0, 0.060, 0.200), (0, 0.035, 0.270), "Spine1"),
    ("Neck", (0, 0.035, 0.270), (0, 0.000, 0.325), "Spine2"),
    ("Head", (0, 0.000, 0.325), (0, -0.020, 0.450), "Neck"),
    ("Tail1", TAIL_PATH[0], TAIL_PATH[2], "Hips"),
    ("Tail2", TAIL_PATH[2], TAIL_PATH[4], "Tail1"),
    ("Tail3", TAIL_PATH[4], TAIL_PATH[6], "Tail2"),
    ("Tail4", TAIL_PATH[6], TAIL_PATH[8], "Tail3"),
]
for _n, _h, _t, _p in LEFT_BONES:
    for _sx, _suf in ((1, "L"), (-1, "R")):
        BONES.append((_n + _suf, (_h[0] * _sx, _h[1], _h[2]), (_t[0] * _sx, _t[1], _t[2]),
                      _p if _p in ("Spine2", "Hips") else _p + _suf))
BONE = {n: (Vector(h), Vector(t)) for n, h, t, p in BONES}


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length


def wfn(names, power=4.0):
    """Веса «по расстоянию до кости»: обратная степень расстояния, две ближайшие кости."""
    def f(p):
        p = Vector(p)
        ds = sorted((max(seg_dist(p, *BONE[n]), 1e-4), n) for n in names)[:2]
        w = {n: d ** -power for d, n in ds}
        tot = sum(w.values())
        return {n: x / tot for n, x in w.items() if x / tot > 0.02}
    return f


# =====================================================================================
#  Геометрия
# =====================================================================================
# Туловище: (z, полуширина, спина Y, грудь/живот Y) — с видов сбоку (спина) и спереди/сзади (ширина).
T_RINGS = [
    (0.008, 0.062, 0.128, 0.028), (0.030, 0.082, 0.146, 0.006), (0.070, 0.088, 0.152, -0.014),
    (0.118, 0.085, 0.156, -0.026), (0.168, 0.080, 0.157, -0.034), (0.212, 0.077, 0.148, -0.040),
    (0.248, 0.074, 0.132, -0.042), (0.278, 0.064, 0.118, -0.036), (0.302, 0.050, 0.098, -0.028),
    (0.326, 0.038, 0.070, -0.022), (0.352, 0.028, 0.040, -0.018),
]
T_COLS = 12
# Голова: (z, полуширина, затылок Y, лицо Y). Подбородок z≈0.297, макушка z≈0.459.
H_RINGS = [
    (0.302, 0.026, 0.005, -0.060), (0.314, 0.044, 0.025, -0.080), (0.330, 0.056, 0.040, -0.094),
    (0.348, 0.061, 0.050, -0.099), (0.366, 0.062, 0.053, -0.099), (0.384, 0.063, 0.054, -0.101),
    (0.402, 0.062, 0.052, -0.104), (0.420, 0.058, 0.044, -0.096), (0.436, 0.050, 0.032, -0.084),
    (0.449, 0.036, 0.016, -0.066),
]
H_COLS = 16
H_MUZZLE = {(2, 0): 0.005, (3, 0): 0.008, (3, 1): 0.003, (2, 1): 0.002, (6, 0): 0.003}   # (кольцо, |колонка|): вперёд
EYES = [(-0.0205, 0.3706), (0.0205, 0.3706)]       # центры глаз (x, z) с вида спереди
HEAD_C = Vector((0.0, -0.022, 0.378))


def orient_tube(mb, fis, path):
    """Нормали наружу от оси трубы (для изогнутых труб общая ориентация из loft не годится)."""
    P = [Vector(p) for p in path]
    for f in fis:
        if f is None:
            continue
        c = mb.fcenter(f)
        best = min(((seg_dist(c, P[i], P[i + 1]), i) for i in range(len(P) - 1)))
        i = best[1]; ab = P[i + 1] - P[i]
        t = max(0.0, min(1.0, (c - P[i]).dot(ab) / ab.length_squared))
        if mb.fnormal(f).dot(c - (P[i] + ab * t)) < 0:
            mb.faces[f] = tuple(reversed(mb.faces[f])); mb.fuv[f] = list(reversed(mb.fuv[f]))
    return fis


def tube(mb, path, radii, nside, isl, tag, w, cap_end=0.6, cap_start=None, ref=(0, 0, 1)):
    """Труба вдоль ломаной path. radii — r или (r_бок, r_верх) на каждую точку. Кольца — параллельный перенос рамки."""
    P = [Vector(p) for p in path]; n = len(P)
    T = []
    for i in range(n):
        d = P[min(i + 1, n - 1)] - P[max(i - 1, 0)]
        T.append(d.normalized())
    up = Vector(ref); up = (up - T[0] * up.dot(T[0])).normalized()
    rings, axis = [], list(P)
    for i in range(n):
        up = (up - T[i] * up.dot(T[i])).normalized()
        side = T[i].cross(up)
        r = radii[i]; rs, ru = (r, r) if not isinstance(r, tuple) else r
        pts = []
        for k in range(nside):
            th = 2 * math.pi * k / nside
            pts.append(P[i] + side * (rs * math.sin(th)) + up * (ru * math.cos(th)))
        rings.append(mb.ring(pts, [w(p) for p in pts]))
    if cap_start is not None:
        r0 = radii[0]; r0 = r0 if not isinstance(r0, tuple) else max(r0)
        pv = P[0] - T[0] * r0 * cap_start
        rings.insert(0, [mb.vert(pv, w(pv))] * nside); axis.insert(0, pv)
    pole = None
    if cap_end:
        r1 = radii[-1]; r1 = r1 if not isinstance(r1, tuple) else max(r1)
        pv = P[-1] + T[-1] * r1 * cap_end
        pole = mb.vert(pv, w(pv)); axis.append(pv)
    fis = loft(mb, rings, isl, tag, seam=nside // 2, pole=pole)
    return orient_tube(mb, fis, axis)


def build_torso(mb):
    w = wfn(["Hips", "Spine1", "Spine2", "Neck"])
    rings = [[mb.vert((0, 0.078, 0.0), w((0, 0.078, 0.0)))] * T_COLS]
    for z, a, yb, yf in T_RINGS:
        yc, d = (yb + yf) / 2, (yb - yf) / 2
        pts = []
        for k in range(T_COLS):
            th = 2 * math.pi * k / T_COLS
            x, y = sellipse(a, d, d, yc, th, 2.2)
            pts.append((x, y, z))
        rings.append(mb.ring(pts, [w(p) for p in pts]))
    top = mb.vert((0, 0.010, 0.368), {"Neck": 0.5, "Head": 0.5})
    loft(mb, rings, "body", "body", seam=T_COLS // 2, pole=top)


def back_profile(z):
    zs = [r[0] for r in T_RINGS]
    for i in range(len(zs) - 1):
        if zs[i] <= z <= zs[i + 1]:
            t = (z - zs[i]) / (zs[i + 1] - zs[i])
            return T_RINGS[i][2] + (T_RINGS[i + 1][2] - T_RINGS[i][2]) * t
    return T_RINGS[-1][2]


def build_head(mb):
    w = lambda p: {"Head": 1.0}
    rings = [[mb.vert((0, -0.030, 0.297), w(0))] * H_COLS]
    for i, (z, a, yb, yf) in enumerate(H_RINGS):
        yc, bf, bb = (yb + yf) / 2, (yb - yf) / 2, (yb - yf) / 2
        pts = []
        for k in range(H_COLS):
            th = 2 * math.pi * k / H_COLS
            front = math.cos(th) > 0
            x, y = sellipse(a, bf, bb, yc, th, 2.6 if front else 2.0)
            kk = min(k, H_COLS - k)
            y -= H_MUZZLE.get((i, kk), 0.0)
            pts.append((x, y, z))
        rings.append(mb.ring(pts, {"Head": 1.0}))
    top = mb.vert((0, -0.028, 0.459), {"Head": 1.0})
    loft(mb, rings, "head", "head", seam=H_COLS // 2, pole=top)


def build_ear(mb, sx):
    """Ухо — чуть выгнутая пластинка 3×3, форма вырезается альфой. Двустороннее (материал без отсечения граней).
    Место — как на концепте сбоку (за глазами, на уровне бровей); смотрит в бок и немного вперёд,
    край у головы (u = 0) утоплен в череп, чтобы не было щели."""
    nrm = Vector((0.70 * sx, -0.68, 0.10)).normalized()
    up = Vector((0, 0, 1)); up = (up - nrm * up.dot(nrm)).normalized()
    side = up.cross(nrm) * sx                      # к краю уха (наружу и назад)
    if side.x * sx < 0:
        side = -side
    W, H = 0.036, 0.048
    root = Vector((0.053 * sx, 0.014, 0.390))
    c = root + side * (W * 0.5)
    rows = []
    for j in range(3):
        row = []
        for i in range(3):
            u, v = i / 2 - 0.5, j / 2 - 0.5
            cup = -0.006 if i == 1 else 0.0         # середина уха — вглубь (раковина)
            p = c + side * (u * W) + up * (v * H) + nrm * (cup + 0.004 * u)
            row.append(p)
        rows.append(mb.ring(row, {"Head": 1.0}))
    loft(mb, rows, "ear" + ("L" if sx > 0 else "R"), "ear", closed=False, mat=1, direction=nrm)


def build_fringe_head(mb):
    """Бахрома вокруг мордочки: макушка и щёки (за ушами — разрыв)."""
    # только щёки и подбородок: на макушке бахрома торчала тёмным «хохолком»
    angs = [-158, -142, -126, 126, 142, 158]
    gaps = {(2, 3)}
    a, h, y0 = 0.062, 0.080, -0.004
    inner, outer = [], []
    for g in angs:
        f = rad(g)
        d = Vector((math.sin(f), 0, math.cos(f)))
        p = Vector((a * 0.93 * math.sin(f), y0, HEAD_C.z + h * 0.93 * math.cos(f)))
        q = p + d * (0.014 if abs(g) < 100 else 0.013) + Vector((0, 0.006, -0.004 if abs(g) > 100 else 0.0))
        inner.append(p); outer.append(q)
    ri = mb.ring(inner, {"Head": 1.0}); ro = mb.ring(outer, {"Head": 1.0})
    loft(mb, [ri, ro], "fringe_head", "fringe", closed=False, mat=1,
         skip=lambda i, j0, j1: (j0, j1) in gaps, direction=Vector((0, -1, 0)))


def build_fringe_back(mb):
    """Бахрома вдоль спины — пушистый контур сбоку."""
    w = wfn(["Hips", "Spine1", "Spine2", "Neck"])
    zs = [0.04, 0.09, 0.14, 0.19, 0.235, 0.27, 0.30, 0.325]
    inner, outer = [], []
    for z in zs:
        yb = back_profile(z)
        p = Vector((0, yb - 0.005, z)); q = Vector((0, yb + 0.015, z - 0.010))
        inner.append(mb.vert(p, w(p))); outer.append(mb.vert(q, w(q)))
    loft(mb, [inner, outer], "fringe_back", "fringe", closed=False, mat=1, direction=Vector((1, 0, 0)))


def build_limbs(mb, sx):
    S_ = "L" if sx > 0 else "R"
    m = lambda p: (p[0] * sx, p[1], p[2])
    arm_w = wfn(["Spine2", "UpperArm" + S_, "Forearm" + S_])
    tube(mb, [m(p) for p in [(0.060, 0.025, 0.258), (0.058, -0.020, 0.210), (0.055, -0.060, 0.168)]],
         [0.030, 0.029, 0.025], 8, "upperarm", "limb", arm_w, cap_end=0.8)
    fw = wfn(["UpperArm" + S_, "Forearm" + S_, "Hand" + S_])
    tube(mb, [m(p) for p in [(0.054, -0.060, 0.172), (0.051, -0.083, 0.100), (0.048, -0.097, 0.042)]],
         [0.023, 0.020, 0.016], 6, "forearm", "limb", fw, cap_end=0.5)
    hw = wfn(["Forearm" + S_, "Hand" + S_])
    tube(mb, [m(p) for p in [(0.048, -0.095, 0.042), (0.049, -0.108, 0.017), (0.050, -0.124, 0.009), (0.050, -0.139, 0.006)]],
         [0.015, (0.018, 0.010), (0.019, 0.007), (0.016, 0.005)], 6, "hand" + S_, "hand", hw, cap_end=0.9)
    tw = wfn(["Hips", "Thigh" + S_, "Shin" + S_])
    tube(mb, [m(p) for p in [(0.055, 0.080, 0.062), (0.080, 0.035, 0.105), (0.100, -0.005, 0.145), (0.112, -0.030, 0.166)]],
         [0.046, 0.052, 0.046, 0.038], 8, "thigh", "limb", tw, cap_end=1.0)
    sw = wfn(["Thigh" + S_, "Shin" + S_, "Foot" + S_])
    tube(mb, [m(p) for p in [(0.113, -0.032, 0.160), (0.109, -0.010, 0.095), (0.105, 0.006, 0.036)]],
         [0.030, 0.027, 0.020], 6, "shin", "limb", sw, cap_end=0.7)
    ftw = wfn(["Shin" + S_, "Foot" + S_])
    tube(mb, [m(p) for p in [(0.104, 0.030, 0.014), (0.108, -0.008, 0.013), (0.115, -0.048, 0.009), (0.121, -0.072, 0.006)]],
         [(0.019, 0.012), (0.021, 0.012), (0.023, 0.008), (0.020, 0.005)], 6, "foot" + S_, "foot", ftw,
         cap_end=0.9, cap_start=0.8)


def build_tail(mb):
    path = [(x, y, max(z, r * 0.9)) for (x, y, z), r in zip(TAIL_PATH, TAIL_R)]
    tube(mb, path, TAIL_R, 6, "tail", "tail", wfn(["Hips", "Tail1", "Tail2", "Tail3", "Tail4"]), cap_end=1.2)


def build_all():
    mb = MB()
    build_torso(mb)
    build_head(mb)
    build_ear(mb, 1); build_ear(mb, -1)
    # бахрому вокруг мордочки не строим: в игре она давала тёмный «хохолок» на макушке и «ошейник» под подбородком
    build_limbs(mb, 1); build_limbs(mb, -1)
    build_tail(mb)
    return mb


# =====================================================================================
#  Концепт → источник цвета
# =====================================================================================
def prep_reference():
    img = bpy.data.images.load(REF_PATH, check_existing=False)
    w, h = img.size
    a = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[::-1, :, :3].copy()
    bpy.data.images.remove(img)
    a = a[:, :1000]                                      # только три вида обезьянки (Юрчик справа не нужен)
    fg0 = np.abs(a - 0.567).max(axis=2) > 0.06
    H, W = fg0.shape; W2 = W + 2
    passable = np.zeros((H + 2, W2), bool); passable[1:-1, 1:-1] = ~fg0
    pas = passable.ravel().tolist(); seen = bytearray((H + 2) * W2)
    stack = []
    for x in range(1, W + 1):
        stack += [W2 + x, H * W2 + x]
    for y in range(1, H + 1):
        stack += [y * W2 + 1, y * W2 + W]
    while stack:
        i = stack.pop()
        if seen[i] or not pas[i]:
            continue
        seen[i] = 1
        stack += [i - 1, i + 1, i - W2, i + W2]
    outside = np.frombuffer(bytes(seen), np.uint8).reshape(H + 2, W2)[1:-1, 1:-1].astype(bool)
    fg = erode(~outside, 2)
    fg[int(GY) - 6:, :] = False                          # линия земли и тень — не мех
    yy, xx = np.mgrid[0:H, 0:W]
    fg &= np.hypot(xx - SIDE_EYE[0], yy - SIDE_EYE[1]) > SIDE_EYE[2]   # глаз вида сбоку: иначе на 3/4 будет третий глаз
    for ex, ey, rx, ry in CONCEPT_EARS:
        fg &= ((xx - ex) / rx) ** 2 + ((yy - ey) / ry) ** 2 > 1.0
    return {"orig": fill_invalid(a, fg, 40)}


def sample(img, px, py):
    return Y["sample"](img, px, py)


def project(refs, P, N, side=1.0, back=1.0):
    wf = np.clip(-N[:, 1], 0, 1) ** 2 + 0.02
    wb = (np.clip(N[:, 1], 0, 1) ** 2 + 0.02) * back
    ws = np.abs(N[:, 0]) ** 2 * side
    pz = GY - P[:, 2] / S
    img = refs["orig"]
    c = (sample(img, CXF + P[:, 0] / S, pz) * wf[:, None] + sample(img, CXB - P[:, 0] / S, pz) * wb[:, None]
         + sample(img, CXS - P[:, 1] / S, pz) * ws[:, None])
    return c / (wf + wb + ws)[:, None]


def mix(a, b, k):
    k = np.asarray(k, np.float32)
    if k.ndim == 1:
        k = k[:, None]
    return a * (1 - k) + b * k


def fur_finish(c, P, N, warm=0.0):
    """Ворс, рыжина снизу, грязь, изморозь и запечённый свет."""
    s = fbm(P[:, 0] * 240 + P[:, 1] * 170, P[:, 2] * 70 + P[:, 1] * 40, 7)
    fine = vnoise(P[:, 0] * 900 + P[:, 1] * 600, P[:, 2] * 260, 9)
    c = c * (0.90 + 0.16 * s + 0.14 * (fine - 0.5))[:, None]
    low = np.clip((0.17 - P[:, 2]) / 0.15, 0, 1)
    k = np.clip(low * 0.45 + warm, 0, 0.75)
    c = mix(c, c * col((1.22, 1.02, 0.74)), k)                       # рыже-золотистый низ (бёдра, хвост)
    dirt = np.clip(fbm(P[:, 0] * 110 + 3, P[:, 1] * 110 + P[:, 2] * 60, 17) - 0.52, 0, 1) * 1.6
    dirt = dirt * (0.10 + 0.90 * np.clip((0.12 - P[:, 2]) / 0.12, 0, 1))
    c = mix(c, c * col((0.62, 0.56, 0.48)), np.clip(dirt, 0, 0.5))   # свалявшийся грязный мех, гуще снизу
    up = np.clip((N[:, 2] - 0.45) / 0.55, 0, 1)
    sp = (vnoise(P[:, 0] * 520, P[:, 1] * 520 + P[:, 2] * 300, 23) > 0.74).astype(np.float32)
    patch = np.clip(fbm(P[:, 0] * 45, P[:, 1] * 45 + P[:, 2] * 30, 29) - 0.45, 0, 1) * 2.5
    c = mix(c, col((0.78, 0.81, 0.86)), np.clip(up * (0.30 * sp + 0.20 * patch), 0, 0.35))   # изморозь на макушке и плечах
    c = c * col((0.92, 0.88, 0.83))                                   # приглушённый тон концепта (в луче фонарика не выгорает)
    light = 0.94 + 0.16 * np.clip(N[:, 2] * 0.5 + 0.5, 0, 1) + 0.05 * np.clip(-N[:, 1], 0, 1)
    ao = 0.78 + 0.22 * np.clip(P[:, 2] / 0.035, 0, 1)
    return c * (light * ao)[:, None]


def face_mask(P, N):
    e = (P[:, 0] / 0.047) ** 2 + ((P[:, 2] - 0.350) / 0.054) ** 2
    return np.clip((1.0 - e) * 3.0, 0, 1) * np.clip((-N[:, 1] - 0.25) * 3, 0, 1) * (P[:, 1] < -0.05)


def paint_eyes(c, P, N):
    front = N[:, 1] < -0.2
    for ex, ez in EYES:
        d = np.hypot(P[:, 0] - ex, P[:, 2] - ez)
        socket = front & (d < 0.0135)
        c = np.where(socket[:, None], mix(c, col((0.30, 0.22, 0.20)), np.clip((0.0135 - d) / 0.003, 0, 1) * 0.6), c)
        iris = front & (d < 0.0098)
        g = np.clip(d / 0.0098, 0, 1)
        ic = mix(col((0.56, 0.38, 0.14)), col((0.30, 0.19, 0.07)), g ** 2)        # янтарно-карий, к краю темнее
        c = np.where(iris[:, None], ic, c)
        c = np.where((front & (d < 0.0042))[:, None], col((0.03, 0.025, 0.02)), c)
        rim = front & (d > 0.0088) & (d < 0.0108)
        c = np.where(rim[:, None], col((0.08, 0.06, 0.05)), c)
        hl = front & (np.hypot(P[:, 0] - ex + 0.0030, P[:, 2] - ez - 0.0032) < 0.0021)
        c = np.where(hl[:, None], col((0.90, 0.88, 0.82)), c)
    return c


def paint_digits(P, N, u, v, base, stops=(0.45, 0.93)):
    """Тёмно-серые голые кисти/стопы с длинными пальцами. u — вокруг (0.5 — сверху), v — от запястья к кончикам."""
    skin = col(base) * (0.82 + 0.3 * fbm(P[:, 0] * 500, P[:, 1] * 500 + P[:, 2] * 300, 41))[:, None]
    fingers = v > stops[0]
    groove = fingers & (np.abs(((u * 10.0) % 1.0) - 0.5) > 0.40)
    skin = skin * np.where(groove, 0.48, 1.0)[:, None]
    knuck = np.exp(-((v - stops[0] - 0.05) / 0.06) ** 2) * (np.abs(u - 0.5) < 0.3)
    skin = skin + col((0.05, 0.045, 0.045)) * knuck[:, None]
    nail = (v > stops[1]) & (np.abs(u - 0.5) < 0.32)
    skin = np.where(nail[:, None], skin * 1.45 + col((0.04, 0.03, 0.03)), skin)
    skin = skin * (0.80 + 0.3 * np.clip(N[:, 2] * 0.5 + 0.5, 0, 1))[:, None]
    return skin


def paint(tag, refs, P, N, LUV):
    n = len(P); alpha = np.ones(n, np.float32)
    u, v = LUV[:, 0], LUV[:, 1]
    if tag == "head":
        # вид сбоку — только для задней половины головы: спереди он отпечатывал на щеках
        # второй профиль (бровь, нос, рот); лицо и щёки берём с вида спереди
        sw = np.clip((P[:, 1] + 0.025) / 0.035, 0, 1)
        c = project(refs, P, N, side=sw)
        # бока передней половины: вид спереди там растягивается полосами — кладём ровный мех
        # цвета боков головы (ворс и свет добавит fur_finish)
        graze = np.clip((np.abs(N[:, 0]) - 0.35) / 0.35, 0, 1) * (1 - sw)
        ref_side = (sw > 0.99) & (np.abs(N[:, 0]) > 0.6)
        base = c[ref_side].mean(axis=0) if ref_side.any() else col((0.31, 0.27, 0.23))
        c = mix(c, np.broadcast_to(base, c.shape), graze)
        fm = face_mask(P, N)
        fur = fur_finish(c, P, N)
        skin = c * col((1.06, 1.0, 0.97)) * (0.92 + 0.12 * vnoise(P[:, 0] * 700, P[:, 2] * 700, 3))[:, None]
        c = mix(fur, skin, fm)
        c = paint_eyes(c, P, N)
    elif tag in ("body", "limb"):
        c = fur_finish(project(refs, P, N, side=1.0), P, N)
    elif tag == "tail":
        # хвост процедурный: на концепте по нему идут контурные линии, при проекции они ложатся полосами
        base = col((0.37, 0.345, 0.31)) * (0.92 + 0.12 * vnoise(u * 3, v * 2, 51))[:, None]
        c = fur_finish(base * (0.85 + 0.25 * np.clip(N[:, 2], 0, 1))[:, None], P, N * np.array([1, 1, 0.3], np.float32), warm=0.10)
    elif tag == "fringe":
        Nn = N.copy(); Nn[:, 1] = np.where(P[:, 1] < 0.02, -0.9, Nn[:, 1])
        c = fur_finish(project(refs, P, Nn, side=0.6), P, Nn) * (0.92 + 0.12 * v)[:, None]
        tri = lambda x: 1 - np.abs((x % 1.0) - 0.5) * 2
        rnd = vnoise(u * 40, u * 3, 47)
        length = 0.30 + 0.70 * (0.5 * tri(u * 26 + 0.3 * np.sin(u * 53)) ** 1.3 + 0.5 * tri(u * 57 + 0.4)) * (0.55 + 0.45 * rnd)
        alpha = (v < length).astype(np.float32)
    elif tag == "ear":
        # форма уха: округлый верх и наружный край, узкое основание у головы (u = 0 — у головы)
        # без прямых углов: у головы ухо сужается к узкой ножке, дальше — округлое (верх шире низа)
        e = ((u - 0.50) / 0.50) ** 2 + ((v - 0.56) / np.where(v > 0.56, 0.44, 0.50)) ** 2
        stem = (u < 0.30) & (np.abs(v - 0.45) < 0.22 - 0.4 * u)
        alpha = ((e < 1.0) | stem).astype(np.float32)
        pink = col((0.50, 0.40, 0.37)) * (0.90 + 0.16 * vnoise(u * 9, v * 9, 13))[:, None]
        cav = np.clip(1.0 - (((u - 0.42) / 0.28) ** 2 + ((v - 0.52) / 0.30) ** 2), 0, 1)
        c = mix(pink, col((0.32, 0.24, 0.22)), cav * 0.60)
        c = mix(c, col((0.40, 0.34, 0.30)), np.clip((e - 0.62) * 3, 0, 1) * 0.70)   # тёмный пушистый край, как на концепте
        c = mix(c, col((0.36, 0.32, 0.28)), np.clip((0.30 - u) / 0.30, 0, 1) * 0.80)  # мех у основания (у головы)
    elif tag == "hand":
        c = paint_digits(P, N, u, v, (0.34, 0.315, 0.30), (0.42, 0.90))
        cuff = np.clip((0.22 - v) / 0.08, 0, 1)
        c = mix(c, fur_finish(project(refs, P, N), P, N), cuff)
    elif tag == "foot":
        c = paint_digits(P, N, u, v, (0.33, 0.305, 0.29), (0.55, 0.92))
        heel = np.clip((0.15 - v) / 0.1, 0, 1) * np.clip(N[:, 2] * 2, 0, 1)
        c = mix(c, fur_finish(project(refs, P, N), P, N), heel)
    else:
        c = np.tile(col((0.03, 0.03, 0.03)), (n, 1))
    return np.clip(c, 0, 1), alpha


# =====================================================================================
#  Атлас, материалы, скелет, анимации, экспорт
# =====================================================================================
def ps2_module():
    spec = importlib.util.spec_from_file_location("ps2_style_monkey", os.path.join(HERE, "ps2_style.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def save_atlas(rgba):
    if not os.environ.get("PS2_OFF"):
        rgba = ps2_module().ps2_pass(rgba, TEX_NAME)
    h, w = rgba.shape[:2]
    img = bpy.data.images.get(TEX_NAME)
    if img and (img.size[0] != w or img.size[1] != h):
        bpy.data.images.remove(img); img = None
    img = img or bpy.data.images.new(TEX_NAME, w, h, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(rgba[::-1]).ravel())
    path = os.path.join(ROOT, "assets", "textures", TEX_NAME + ".png")
    img.filepath_raw = path; img.file_format = 'PNG'
    img.save()
    img.filepath = path
    return img


def set_scene(sc):
    if bpy.context.window is not None and bpy.context.window.scene is not sc:
        bpy.context.window.scene = sc


def select_only(sc, obs, active):
    set_scene(sc)
    vl = bpy.context.view_layer
    vl.update()
    for o in sc.objects:
        o.select_set(o in obs)
    vl.objects.active = active


def rig(ob, used, mb, sc):
    arm_data = bpy.data.armatures.new("MonkeyRig")
    arm = bpy.data.objects.new("Monkey", arm_data)
    sc.collection.objects.link(arm)
    select_only(sc, [arm], arm)
    bpy.ops.object.mode_set(mode='EDIT')
    for n, h, t, p in BONES:
        b = arm_data.edit_bones.new(n)
        b.head = h; b.tail = t; b.roll = 0.0
        if p:
            b.parent = arm_data.edit_bones[p]
            b.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    groups = {n: ob.vertex_groups.new(name=n) for n, *_ in BONES}
    for k, vid in enumerate(used):
        w = {b: x for b, x in mb.w[vid].items() if x > 1e-4}
        tot = sum(w.values())
        for b, x in w.items():
            groups[b].add([k], x / tot, 'REPLACE')
    ob.parent = arm
    mod = ob.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
    return arm


# --- анимации: повороты задаём вокруг осей «мира» (оси скелета в покое) ---
AX = {"x": Vector((1, 0, 0)), "y": Vector((0, 1, 0)), "z": Vector((0, 0, 1))}


def qw(arm, bone, rots):
    """rots — [(ось, градусы)], ось в пространстве скелета. Возвращает кватернион в локальном пространстве кости."""
    rq = arm.data.bones[bone].matrix_local.to_quaternion()
    q = Quaternion()
    for ax, deg in rots:
        a = rq.inverted() @ AX[ax]
        q = Quaternion(a, rad(deg)) @ q
    return q


def wave(t, period, phase=0.0):
    return math.sin(2 * math.pi * (t / period + phase))


def pose_idle(arm, t, L):
    b = 2 * math.pi
    breath = wave(t, L / 2)                                          # два вдоха за цикл
    yaw = 12 * math.sin(b * t / L)
    tilt = 7 * math.sin(b * t / L + 1.3)
    nod = 3 * math.sin(b * t / L * 2 + 0.4)
    p = {
        "Spine1": [("x", 1.2 * breath)],
        "Spine2": [("x", 1.5 * breath)],
        "Neck": [("x", -1.5 * breath + nod * 0.4), ("z", yaw * 0.35)],
        "Head": [("x", nod), ("z", yaw * 0.65), ("y", tilt)],
        "UpperArmL": [("x", -1.0 * breath)], "UpperArmR": [("x", -1.0 * breath)],
    }
    for i in range(4):
        p["Tail%d" % (i + 1)] = [("z", 6 * math.sin(b * t / L * 2 - i * 0.7))]
    return p


def pose_look(arm, t, L):
    # смотрит влево — пауза — вправо — пауза — обратно
    keys = [(0.0, 0, 0), (0.6, 0, 0), (1.2, 42, 6), (2.0, 42, 4), (2.6, -36, -5), (3.4, -36, -3), (4.0, 0, 0)]
    for i in range(len(keys) - 1):
        if keys[i][0] <= t <= keys[i + 1][0]:
            k = smooth((t - keys[i][0]) / (keys[i + 1][0] - keys[i][0]))
            yaw = keys[i][1] + (keys[i + 1][1] - keys[i][1]) * k
            tilt = keys[i][2] + (keys[i + 1][2] - keys[i][2]) * k
            break
    p = pose_idle(arm, t, L)
    p["Spine2"] = p["Spine2"] + [("z", yaw * 0.15)]
    p["Neck"] = [("z", yaw * 0.35), ("x", -2)]
    p["Head"] = [("z", yaw * 0.55), ("y", tilt), ("x", 4 * abs(yaw) / 42)]
    return p


def pose_eat(arm, t, L):
    """Правая кисть ко рту, жуёт (кивки головой), снова опускает. Руку ведём через IK, см. bake_ik."""
    lift = smooth(t / 0.7) * (1 - smooth((t - 2.3) / 0.7))
    chew = math.sin(2 * math.pi * t * 3.0) * lift
    p = pose_idle(arm, t, L)
    p["Head"] = [("x", 10 * lift + 2.5 * chew), ("z", 4 * lift)]
    p["Neck"] = [("x", 4 * lift)]
    p["Spine2"] = [("x", 3 * lift), ("z", -3 * lift)]
    return p, lift


def key_pose(arm, pose, f):
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = qw(arm, pb.name, pose.get(pb.name, []))
        pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)


def push_nla(arm, ac, name):
    ad = arm.animation_data
    tr = ad.nla_tracks.new(); tr.name = name; tr.mute = True
    st = tr.strips.new(name, 0, ac); st.name = name
    ad.action = None


def new_action(arm, name):
    ad = arm.animation_data or arm.animation_data_create()
    old = bpy.data.actions.get(name)
    if old:
        bpy.data.actions.remove(old)
    ac = bpy.data.actions.new(name)
    ad.action = ac
    return ac


def make_anim(arm, sc, name, L, fn):
    ac = new_action(arm, name)
    N = int(round(L * FPS))
    for f in range(0, N + 1, 2):
        t = f / FPS
        key_pose(arm, fn(arm, t if f < N else 0.0, L), f)
    push_nla(arm, ac, name)
    return {"frames": N + 1, "len_s": L}


EAT_WRIST = (-0.030, -0.088, 0.262)     # запястье под подбородком
EAT_MOUTH = (-0.004, -0.110, 0.318)     # кончики пальцев — у рта
EAT_POLE = (-0.075, -0.080, 0.080)      # локоть смотрит вниз-вбок, а не к уху
EAT_POLE_ANGLE = -90.0


def make_eat(arm, sc, L=3.0):
    """Еда: поза головы/спины — ключами, правая рука — IK к точке у рта, затем запекаем в повороты костей."""
    tgt = bpy.data.objects.new("MonkeyEatTarget", None)
    sc.collection.objects.link(tgt)
    pole = bpy.data.objects.new("MonkeyEatPole", None)
    sc.collection.objects.link(pole)
    pole.location = EAT_POLE
    pbF = arm.pose.bones["ForearmR"]
    ik = pbF.constraints.new('IK'); ik.target = tgt; ik.chain_count = 2
    ik.pole_target = pole; ik.pole_angle = rad(EAT_POLE_ANGLE)
    rest_hand = BONE["HandR"][0]
    mouth = Vector(EAT_WRIST)                          # куда встаёт запястье: пальцы тогда у рта
    N = int(round(L * FPS))
    mats = {}
    chain = ["UpperArmR", "ForearmR", "HandR"]
    for f in range(0, N + 1, 2):
        t = f / FPS if f < N else 0.0
        pose, lift = pose_eat(arm, t, L)
        for pb in arm.pose.bones:
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = qw(arm, pb.name, pose.get(pb.name, []))
        tgt.location = rest_hand.lerp(mouth, lift)
        bpy.context.view_layer.update()
        # кисть — пальцами на рот (по мере подъёма руки)
        pbH = arm.pose.bones["HandR"]
        M = pbH.matrix.copy(); head = M.translation.copy()
        cur = (M.to_3x3() @ Vector((0, 1, 0))).normalized()
        rd = Quaternion().slerp(cur.rotation_difference((Vector(EAT_MOUTH) - head).normalized()), lift)
        R = rd.to_matrix() @ M.to_3x3()
        pbH.matrix = Matrix.Translation(head) @ R.to_4x4()
        bpy.context.view_layer.update()
        mats[f] = {n: arm.pose.bones[n].matrix.copy() for n in chain}
    pbF.constraints.remove(ik)
    bpy.data.objects.remove(tgt, do_unlink=True); bpy.data.objects.remove(pole, do_unlink=True)
    ac = new_action(arm, "Eat")
    for f in sorted(mats):
        t = f / FPS if f < N else 0.0
        pose, lift = pose_eat(arm, t, L)
        for pb in arm.pose.bones:
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = qw(arm, pb.name, pose.get(pb.name, []))
        bpy.context.view_layer.update()
        for n in chain:
            arm.pose.bones[n].matrix = mats[f][n]
            bpy.context.view_layer.update()
        for pb in arm.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
    push_nla(arm, ac, "Eat")
    return {"frames": N + 1, "len_s": L}


def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion(); pb.location = (0, 0, 0)


def export_gltf(sc, arm, body):
    select_only(sc, [arm, body], arm)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(ROOT, "assets", "models", "monkey.gltf"), use_selection=True, use_active_scene=True,
        export_format='GLTF_SEPARATE', export_keep_originals=True, export_apply=False, export_skins=True,
        export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
        export_frame_step=1, export_optimize_animation_size=True, export_anim_single_armature=True,
        export_def_bones=False, export_reset_pose_bones=True, export_bake_animation=False)


def preview(sc, body):
    """Превью спереди / сбоку / сзади / 3/4 — для сравнения с концептом."""
    if not PREVIEW:
        return
    os.makedirs(PREVIEW, exist_ok=True)
    keep = (sc.render.engine, sc.camera)
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'FLAT'; sc.display.shading.color_type = 'TEXTURE'
    sc.render.resolution_x, sc.render.resolution_y = 600, 600
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    w = bpy.data.worlds.get("MonkeyPreview") or bpy.data.worlds.new("MonkeyPreview")
    w.color = (0.32, 0.32, 0.32); sc.world = w
    cam_d = bpy.data.cameras.new("MonkeyPrevCam"); cam_d.type = 'ORTHO'; cam_d.ortho_scale = 0.62
    cam = bpy.data.objects.new("MonkeyPrevCam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
    for tag, d in (("front", Vector((0, -1, 0))), ("side", Vector((1, 0, 0))), ("back", Vector((0, 1, 0))),
                   ("q34", Vector((0.7, -1, 0.35)))):
        d = d.normalized()
        cam.location = Vector((0.0, 0.03, 0.23)) + d * 3
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(PREVIEW, "monkey_%s.png" % tag)
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True); bpy.data.cameras.remove(cam_d)
    sc.render.engine = keep[0]; sc.camera = keep[1]


def scene_extras(sc):
    cam_d = bpy.data.cameras.get("MonkeyCamera") or bpy.data.cameras.new("MonkeyCamera")
    cam_d.lens = 60.0
    cam = bpy.data.objects.new("MonkeyCamera", cam_d); sc.collection.objects.link(cam)
    target = Vector((0.0, 0.02, 0.22)); d = Vector((0.55, -0.82, 0.25)).normalized()
    cam.location = target + d * 1.6
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    sun_d = bpy.data.lights.get("MonkeySun") or bpy.data.lights.new("MonkeySun", 'SUN')
    sun = bpy.data.objects.new("MonkeySun", sun_d); sc.collection.objects.link(sun)
    sun.rotation_euler = Vector((0.35, 0.6, -0.72)).to_track_quat('-Z', 'Y').to_euler()


# =====================================================================================
def main():
    sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    set_scene(sc)
    for ob in list(sc.objects):
        if ob.mode != 'OBJECT':
            select_only(sc, [ob], ob)
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.armatures, bpy.data.cameras):
        for d in list(blk):
            if d.users == 0 and d.name.startswith("Monkey"):
                blk.remove(d)
    sc.render.fps = FPS; sc.render.fps_base = 1.0

    Y["ATLAS"] = ATLAS
    Y["ISL_DENS"] = {"head": 3.0, "earL": 1.6, "earR": 1.6, "fringe_head": 1.6, "fringe_back": 0.8, "handL": 1.4,
                     "handR": 1.4, "footL": 1.2, "footR": 1.2, "tail": 0.9, "body": 1.0}
    Y["paint"] = paint
    mb = build_all()
    D, pos = Y["pack_islands"](mb, size=ATLAS, pad=2)
    img = bpy.data.images.get(TEX_NAME)
    mats = [Y["make_material"]("MonkeyFur", img, False), Y["make_material"]("MonkeyFringe", img, True)]
    body, fsel, used = Y["make_object"](mb, 0, "MonkeyMesh", sc.collection, mats)
    info = {"tris": sum(len(mb.faces[f]) - 2 for f in fsel), "verts": len(used), "atlas": ATLAS,
            "density_px_per_m": round(D, 1)}

    refs = prep_reference()
    rgba, Tb = Y["bake_atlas"](mb, {0: (body.data, fsel)}, refs)
    img = save_atlas(rgba)
    for m, a in zip(mats, (False, True)):
        Y["make_material"](m.name, img, a)
    info["atlas_fill"] = round(float((Tb >= 0).mean()), 3)

    arm = rig(body, used, mb, sc)
    select_only(sc, [arm], arm)
    bpy.ops.object.mode_set(mode='POSE')
    info["anims"] = {
        "Idle": make_anim(arm, sc, "Idle", 3.6, pose_idle),
        "LookAround": make_anim(arm, sc, "LookAround", 4.0, pose_look),
        "Eat": make_eat(arm, sc, 3.0),
    }
    reset_pose(arm)
    bpy.ops.object.mode_set(mode='OBJECT')
    export_gltf(sc, arm, body)
    preview(sc, body)
    scene_extras(sc)
    # в окне Blender показываем Idle
    ad = arm.animation_data
    ad.action = bpy.data.actions.get("Idle")
    sc.frame_start, sc.frame_end = 0, int(3.6 * FPS)
    select_only(sc, [arm], arm)
    info["bones"] = len(BONES)
    print("BUILD_MONKEY " + json.dumps(info))
    return info


result = main()
