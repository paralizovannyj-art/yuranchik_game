# -*- coding: utf-8 -*-
# Хьюга (YUR-22): пегий французский бульдог, low-poly модель в стиле PS2 по фото docs/references/hyuga/hyuga_photo_*.png
#   side  — правый бок (чёрное седло на плече и правой передней лапе, пятно на середине спины, пятно на крупе);
#   back  — сверху-сзади (три пятна по хребту, белая шея, оранжевый ошейник);
#   front — спереди-сверху (тёмная тигровая голова с белой проточиной, седая морда, розовое пятнышко у носа).
#
# Устроено так же, как макака (tools/blender/build_monkey.py) и Юрчик (build_yurchik_v3.py) — помощники берутся оттуда:
#   1. Геометрия — «кольца»-сечения, соединённые в трубы: туловище — кольца поперёк спины, голова — горизонтальные
#      кольца (как у макаки), шея, лапы, хвостик и ошейник — трубы вдоль кости. Уши-«летучая мышь» — две изогнутые
#      пластинки (внутренняя и наружная сторона), форма вырезается альфой.
#   2. Развёртка — прямоугольные островки, упакованные в один атлас 256×256.
#   3. Текстура — процедурная (ортогонального концепта нет, только фото): белая шерсть, чёрные тигровые пятна
#      заданы 3D-эллипсоидами по фото, голова, глаза, нос, проточина, ошейник. Свет запечён в текстуру.
#   4. Скелет — свой: таз, 2 позвонка, шея, голова, уши, хвост; передние лапы по 3 кости, задние по 4. Поза покоя — стоит.
#   5. Анимации — процедурные ключи: Idle (4 с), Walk (рысь на месте, 0.8 с), Sniff (нюхает землю, 3 с),
#      LookAround (4 с). Все зациклены.
#
# Масштаб: французский бульдог в холке ≈ 0.30 м, макушка ≈ 0.45 м, кончики ушей ≈ 0.52 м
# (Юрчик — 1.783 м: собака ему чуть ниже колена).
# Оси Blender: Z — вверх, собака смотрит в −Y (в Godot это +Z), её левая сторона — +X. Начало координат — на земле
# под серединой тела.
#
# Запуск — через Blender MCP в открытом Blender (сцена «Hyuga» создаётся заново, остальные сцены не трогаются):
#   exec(open(r"<проект>\tools\blender\build_hyuga.py", encoding="utf-8").read(),
#        {"__file__": r"<проект>\tools\blender\build_hyuga.py", "HYUGA_PREVIEW": r"<папка для превью>"})
# Результат: assets/models/hyuga.gltf (+ .bin), assets/textures/hyuga.png.
import bpy, os, sys, math, json, importlib.util
import numpy as np
from mathutils import Vector, Matrix, Quaternion

HERE = os.path.dirname(os.path.abspath(globals().get("__file__") or __file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
_ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = globals().get("HYUGA_PREVIEW") or (_ARGS[0] if _ARGS else None)
TEX_NAME = "hyuga"
SCENE = "Hyuga"
ATLAS = 256
FPS = 30


def load(name, cut):
    src = open(os.path.join(HERE, name), encoding="utf-8").read()
    ns = {"YUR_ROOT": ROOT, "__file__": os.path.join(HERE, name)}
    exec(compile(src[:src.rindex(cut)], name, "exec"), ns)
    return ns


M = load("build_monkey.py", "\nresult = main()")          # трубы, анимационные помощники
Y = M["Y"]                                                  # сетка, атлас, материалы (build_yurchik_v3.py)
MB, loft, sgnpow = Y["MB"], Y["loft"], Y["sgnpow"]
vnoise, fbm, col, rad, smooth, sellipse = Y["vnoise"], Y["fbm"], Y["col"], Y["rad"], Y["smooth"], Y["sellipse"]
tube, mix, qw, seg_dist = M["tube"], M["mix"], M["qw"], M["seg_dist"]
set_scene, select_only = M["set_scene"], M["select_only"]

# =====================================================================================
#  Скелет: (имя, голова, хвост, родитель). Правая сторона — зеркало левой.
# =====================================================================================
LEFT_BONES = [
    ("Shoulder", (0.074, -0.102, 0.215), (0.084, -0.111, 0.125), "Spine2"),
    ("Forearm", (0.084, -0.111, 0.125), (0.082, -0.114, 0.030), "Shoulder"),
    ("Paw", (0.082, -0.114, 0.030), (0.090, -0.150, 0.010), "Forearm"),
    ("Thigh", (0.062, 0.148, 0.222), (0.078, 0.112, 0.130), "Hips"),
    ("Shin", (0.078, 0.112, 0.130), (0.073, 0.166, 0.066), "Thigh"),
    ("Hock", (0.073, 0.166, 0.066), (0.071, 0.162, 0.020), "Shin"),
    ("Foot", (0.071, 0.162, 0.020), (0.071, 0.126, 0.010), "Hock"),
    ("Ear", (0.052, -0.198, 0.414), (0.090, -0.196, 0.505), "Head"),
]
BONES = [
    ("Hips", (0, 0.140, 0.238), (0, 0.040, 0.238), None),
    ("Spine1", (0, 0.040, 0.238), (0, -0.060, 0.232), "Hips"),
    ("Spine2", (0, -0.060, 0.232), (0, -0.112, 0.240), "Spine1"),
    ("Neck", (0, -0.112, 0.258), (0, -0.178, 0.338), "Spine2"),
    ("Head", (0, -0.178, 0.338), (0, -0.205, 0.450), "Neck"),
    ("Tail", (0, 0.198, 0.248), (0, 0.214, 0.220), "Hips"),
]
for _n, _h, _t, _p in LEFT_BONES:
    for _sx, _suf in ((1, "L"), (-1, "R")):
        BONES.append((_n + _suf, (_h[0] * _sx, _h[1], _h[2]), (_t[0] * _sx, _t[1], _t[2]),
                      _p if _p in ("Spine2", "Hips", "Head") else _p + _suf))
BONE = {n: (Vector(h), Vector(t)) for n, h, t, p in BONES}

# Части строятся в «чертёжных» координатах (как размечено выше), затем приводятся к пропорциям бульдога:
# корпус и лапы сжаты по длине (SY), голова увеличена и опущена к груди на короткую шею.
# Шея с ошейником строятся сразу в итоговых координатах — между корпусом и головой.
SY = 0.88
HEAD_PIVOT = Vector((0, -0.180, 0.335))
HEAD_S = 1.12
HEAD_T = Vector((0, 0.034, -0.044))


def xf_body(p):
    return Vector((p[0], p[1] * SY, p[2]))


def xf_head(p):
    return HEAD_PIVOT + (Vector(p) - HEAD_PIVOT) * HEAD_S + HEAD_T


def inv_body(P):
    return P * np.array([1, 1 / SY, 1], np.float32)


def inv_head(P):
    pv, t = np.array(HEAD_PIVOT, np.float32), np.array(HEAD_T, np.float32)
    return (P - pv - t) / HEAD_S + pv


def bone_final(n, h, t):
    if n == "Head" or n.startswith("Ear"):
        return xf_head(h), xf_head(t)
    if n == "Neck":
        return xf_body(h), xf_head(t)
    return xf_body(h), xf_body(t)


BONE_F = {n: bone_final(n, Vector(h), Vector(t)) for n, h, t, p in BONES}


def wfn(names, power=4.0, bones=BONE):
    """Веса «по расстоянию до кости»: обратная степень расстояния, две ближайшие кости."""
    def f(p):
        p = Vector(p)
        ds = sorted((max(seg_dist(p, *bones[n]), 1e-4), n) for n in names)[:2]
        w = {n: d ** -power for d, n in ds}
        tot = sum(w.values())
        return {n: x / tot for n, x in w.items() if x / tot > 0.02}
    return f


# =====================================================================================
#  Геометрия
# =====================================================================================
# Туловище: сечения поперёк спины (y, центр z, полуширина, вверх, вниз). Грудь широкая и глубокая,
# талия поджата, над поясницей лёгкий «горбик», круп круглый.
T_ST = [
    (-0.150, 0.205, 0.084, 0.058, 0.088), (-0.122, 0.214, 0.094, 0.088, 0.118), (-0.078, 0.220, 0.104, 0.088, 0.120),
    (-0.028, 0.225, 0.104, 0.080, 0.100), (0.022, 0.232, 0.093, 0.068, 0.072), (0.072, 0.237, 0.086, 0.064, 0.060),
    (0.118, 0.238, 0.092, 0.066, 0.064), (0.158, 0.237, 0.088, 0.062, 0.066), (0.190, 0.236, 0.070, 0.050, 0.058),
    (0.208, 0.234, 0.042, 0.032, 0.040),
]
T_FRONT, T_REAR = (0, -0.168, 0.195), (0, 0.217, 0.233)
T_COLS = 12
T_EXP = 2.4

# Голова: горизонтальные кольца (z, полуширина, затылок Y, лицо Y). Подбородок z≈0.288, макушка z≈0.452.
H_RINGS = [
    (0.292, 0.048, -0.196, -0.262), (0.305, 0.068, -0.172, -0.276), (0.322, 0.078, -0.158, -0.282),
    (0.340, 0.079, -0.150, -0.282), (0.358, 0.077, -0.147, -0.274), (0.376, 0.076, -0.148, -0.266),
    (0.394, 0.074, -0.150, -0.262), (0.412, 0.071, -0.154, -0.256), (0.428, 0.066, -0.160, -0.248),
    (0.441, 0.058, -0.170, -0.238), (0.449, 0.044, -0.184, -0.224),
]
H_COLS = 16
# морда: короткая, широкая, нос чуть впереди лба; (кольцо, |колонка|): вперёд
H_MUZZLE = {(1, 0): 0.010, (1, 1): 0.008, (2, 0): 0.019, (2, 1): 0.015, (2, 2): 0.005, (3, 0): 0.023,
            (3, 1): 0.017, (3, 2): 0.007, (4, 0): 0.017, (4, 1): 0.011, (5, 0): 0.004}
H_JOWL = {(0, 2): 0.009, (0, 3): 0.009, (1, 2): 0.016, (1, 3): 0.014, (1, 4): 0.007, (2, 2): 0.012,
          (2, 3): 0.010, (2, 4): 0.005}      # брыли: щёки свисают вниз-наружу
EYES = [(-0.040, 0.376), (0.040, 0.376)]          # центры глаз (x, z) на лице
NECK = [xf_body((0, -0.100, 0.248)), xf_head((0, -0.185, 0.350))]   # итоговые координаты
NECK_R = [(0.082, 0.076), (0.074, 0.070)]          # (бок, вперёд) внизу и вверху шеи: короткая и толстая
NECK_SIDES = 10


def build_torso(mb):
    w = wfn(["Hips", "Spine1", "Spine2"])
    rings = [[mb.vert(T_FRONT, w(T_FRONT))] * T_COLS]
    e = 2.0 / T_EXP
    for y, zc, a, rt, rb in T_ST:
        pts = []
        for k in range(T_COLS):
            th = 2 * math.pi * k / T_COLS                     # 0 — спина, 90° — левый бок (+X)
            s, c = math.sin(th), math.cos(th)
            pts.append((a * sgnpow(s, e), y, zc + (rt if c >= 0 else rb) * sgnpow(c, e)))
        rings.append(mb.ring(pts, [w(p) for p in pts]))
    rear = mb.vert(T_REAR, w(T_REAR))
    loft(mb, rings, "body", "body", seam=T_COLS // 2, pole=rear)


def neck_at(t):
    p = NECK[0].lerp(NECK[1], t)
    r0, r1 = NECK_R
    return p, (r0[0] + (r1[0] - r0[0]) * t, r0[1] + (r1[1] - r0[1]) * t)


def build_neck(mb):
    w = wfn(["Spine2", "Neck", "Head"], bones=BONE_F)
    ts = [0.0, 0.5, 1.0]
    path = [neck_at(t)[0] for t in ts]; radii = [neck_at(t)[1] for t in ts]
    tube(mb, path, radii, NECK_SIDES, "neck", "neck", w, cap_end=0, ref=(0, -1, 0))


def build_collar(mb):
    """Оранжевый ошейник: кольцо чуть шире шеи, те же сечения, что у шеи (кадр трубы совпадает)."""
    w = wfn(["Spine2", "Neck", "Head"], bones=BONE_F)
    ts = [0.46, 0.52, 0.58]
    path, radii = [], []
    for t, grow in zip(ts, (0.0035, 0.0055, 0.0035)):
        p, (rs, ru) = neck_at(t)
        path.append(p); radii.append((rs + grow, ru + grow))
    # шея — прямая, поэтому рамка tube() (от ref) везде одна и та же: вершины ошейника стоят ровно над вершинами шеи
    tube(mb, path, radii, NECK_SIDES, "collar", "collar", w, cap_end=0, ref=(0, -1, 0))


def build_head(mb):
    w = {"Head": 1.0}
    rings = [[mb.vert((0, -0.230, 0.287), w)] * H_COLS]
    for i, (z, a, yb, yf) in enumerate(H_RINGS):
        yc, d = (yb + yf) / 2, (yb - yf) / 2
        pts = []
        for k in range(H_COLS):
            th = 2 * math.pi * k / H_COLS                     # 0 — лицо (−Y), 90° — левая щека (+X)
            front = math.cos(th) > 0
            x, y = sellipse(a, d, d, yc, th, 2.7 if front else 2.1)
            kk = min(k, H_COLS - k)
            y -= H_MUZZLE.get((i, kk), 0.0)
            jw = H_JOWL.get((i, kk), 0.0)
            x += math.copysign(jw * 0.5, x) if abs(x) > 1e-6 else 0.0
            pts.append((x, y, z - jw))
        rings.append(mb.ring(pts, w))
    top = mb.vert((0, -0.204, 0.451), w)
    loft(mb, rings, "head", "head", seam=H_COLS // 2, pole=top)


def build_ear(mb, sx):
    """Ухо «летучая мышь»: высокое, с широким основанием и круглым верхом, раскрыто вперёд и чуть наружу.
    Две пластинки: внутренняя (розоватая раковина, смотрит вперёд) и наружная (чёрная), между ними 3.5 мм."""
    S_ = "L" if sx > 0 else "R"
    up = Vector((0.42 * sx, 0.05, 1.0)).normalized()
    nrm = Vector((0.30 * sx, -1.0, 0.0)); nrm = (nrm - up * nrm.dot(up)).normalized()
    side = nrm.cross(up)
    if side.x * sx < 0:
        side = -side
    W, H = 0.072, 0.108
    base = Vector((0.052 * sx, -0.198, 0.414))
    w = wfn(["Head", "Ear" + S_])
    for layer, off, tag in (("in", 0.0, "ear_in"), ("out", -0.0035, "ear_out")):
        rows = []
        for j in range(5):
            v = j / 4
            row = []
            for i in range(4):
                u = i / 3 - 0.5
                cup = -0.012 * (1 - (2 * u) ** 2) * math.sin(math.pi * min(v * 1.1, 1.0))   # раковина: середина вглубь
                taper = 1.0 - 0.08 * v                                                          # к верху чуть уже
                p = base + side * (u * W * taper) + up * (v * H - 0.012) + nrm * (cup + off)
                row.append(p)
            rows.append(mb.ring(row, [w(p) for p in row]))
        d = nrm if layer == "in" else -nrm
        loft(mb, rows, "ear%s_%s" % (S_, layer), tag, closed=False, mat=1, direction=d)


def build_legs(mb, sx):
    S_ = "L" if sx > 0 else "R"
    m = lambda pts: [(p[0] * sx, p[1], p[2]) for p in pts]
    fwd = (0, -1, 0)
    # передняя: плечо (широкое, уходит в грудь), предплечье, лапа
    tube(mb, m([(0.066, -0.104, 0.222), (0.077, -0.112, 0.168), (0.084, -0.111, 0.122)]),
         [(0.034, 0.048), (0.032, 0.038), 0.029], 8, "f_upper" + S_, "leg_f",
         wfn(["Spine2", "Shoulder" + S_, "Forearm" + S_]), cap_end=0.5, ref=fwd)
    tube(mb, m([(0.084, -0.111, 0.128), (0.083, -0.113, 0.078), (0.082, -0.114, 0.030)]),
         [0.028, 0.024, 0.021], 6, "f_fore" + S_, "leg_f", wfn(["Shoulder" + S_, "Forearm" + S_, "Paw" + S_]),
         cap_end=0, ref=fwd)
    tube(mb, m([(0.082, -0.100, 0.021), (0.086, -0.124, 0.017), (0.091, -0.147, 0.012)]),
         [(0.022, 0.021), (0.026, 0.017), (0.022, 0.011)], 8, "f_paw" + S_, "paw",
         wfn(["Forearm" + S_, "Paw" + S_]), cap_end=0.9, cap_start=0.8)
    # задняя: мощное бедро, голень, плюсна, лапа
    tube(mb, m([(0.058, 0.152, 0.228), (0.070, 0.136, 0.178), (0.078, 0.113, 0.130)]),
         [(0.054, 0.060), (0.050, 0.054), 0.035], 8, "r_thigh" + S_, "leg_r",
         wfn(["Hips", "Thigh" + S_, "Shin" + S_]), cap_end=0.6, ref=fwd)
    tube(mb, m([(0.078, 0.113, 0.134), (0.076, 0.140, 0.098), (0.073, 0.166, 0.064)]),
         [0.032, 0.026, 0.021], 6, "r_shin" + S_, "leg_r", wfn(["Thigh" + S_, "Shin" + S_, "Hock" + S_]),
         cap_end=0, ref=fwd)
    tube(mb, m([(0.073, 0.166, 0.070), (0.072, 0.163, 0.042), (0.071, 0.160, 0.022)]),
         [0.021, 0.019, 0.019], 6, "r_hock" + S_, "leg_r", wfn(["Shin" + S_, "Hock" + S_, "Foot" + S_]),
         cap_end=0, ref=fwd)
    tube(mb, m([(0.071, 0.172, 0.020), (0.071, 0.150, 0.016), (0.071, 0.128, 0.012)]),
         [(0.021, 0.020), (0.024, 0.016), (0.021, 0.011)], 8, "r_paw" + S_, "paw",
         wfn(["Hock" + S_, "Foot" + S_]), cap_end=0.9, cap_start=0.8)


def build_tail(mb):
    tube(mb, [(0, 0.198, 0.246), (0, 0.209, 0.234), (0, 0.213, 0.221)], [0.016, 0.013, 0.008], 6,
         "tail", "tail", wfn(["Hips", "Tail"]), cap_end=1.0)


def build_all():
    mb = MB()
    parts = []                                              # (начало, конец, преобразование) по вершинам

    def part(fn, xf):
        a = len(mb.co); fn(); parts.append((a, len(mb.co), xf))
    part(lambda: build_torso(mb), xf_body)
    part(lambda: (build_neck(mb), build_collar(mb)), None)
    part(lambda: (build_head(mb), build_ear(mb, 1), build_ear(mb, -1)), xf_head)
    part(lambda: (build_legs(mb, 1), build_legs(mb, -1), build_tail(mb)), xf_body)
    for a, b, xf in parts:
        if xf:
            for i in range(a, b):
                mb.co[i] = xf(mb.co[i])
    return mb


# =====================================================================================
#  Раскраска (процедурная, по фото)
# =====================================================================================
WHITE = (0.84, 0.83, 0.80)
BLACK = (0.075, 0.070, 0.070)
# чёрные пятна: (центр, полуоси) — эллипсоиды в метрах; правый бок — −X
PATCHES = [
    ((-0.058, -0.050, 0.235), (0.095, 0.058, 0.110)),    # седло на правом плече: от холки до лапы, шея белая
    ((0.035, -0.035, 0.300), (0.040, 0.022, 0.030)),     # язычок седла через холку влево (фото сзади)
    ((-0.030, 0.020, 0.285), (0.095, 0.055, 0.080)),     # пятно на середине спины, свисает на правый бок
    ((0.000, 0.172, 0.272), (0.108, 0.066, 0.085)),      # круп: накрывает обе ляжки и корень хвоста
    ((-0.070, 0.180, 0.222), (0.045, 0.040, 0.040)),     # с крупа на задний край бёдер
    ((0.070, 0.180, 0.222), (0.045, 0.040, 0.040)),
]


def black_mask(P, seed=0):
    m = np.zeros(len(P), np.float32)
    for k, (c, r) in enumerate(PATCHES):
        d = (((P - np.array(c, np.float32)) / np.array(r, np.float32)) ** 2).sum(axis=1)
        n = fbm(P[:, 0] * 70 + P[:, 1] * 45 + k * 3.1, P[:, 2] * 70 + P[:, 1] * 30, 61 + k) - 0.5
        m = np.maximum(m, np.clip((1.0 - d + 0.45 * n) * 7.0, 0, 1))
    return m


def brindle(P):
    """Чёрный тигровый окрас: почти чёрный с редкими серыми прядками."""
    streak = vnoise(P[:, 0] * 260 + P[:, 1] * 260, P[:, 2] * 55, 71)
    fleck = vnoise(P[:, 0] * 900 + P[:, 1] * 700, P[:, 2] * 900, 73)
    k = np.clip((streak - 0.50) * 1.6, 0, 0.55) * 0.8 + np.clip((fleck - 0.80) * 2.5, 0, 0.35)
    return mix(np.tile(col(BLACK), (len(P), 1)), col((0.30, 0.27, 0.24)), k)


def white_coat(P):
    s = fbm(P[:, 0] * 160 + P[:, 1] * 120, P[:, 2] * 90 + P[:, 1] * 40, 81)
    return col(WHITE) * (0.95 + 0.08 * s)[:, None] * col((1.0, 0.99, 0.97))


def finish(c, P, N, dirt_k=1.0):
    """Короткая шерсть, грязь со снега на лапах, лёгкая изморозь на спине, запечённый свет."""
    fine = vnoise(P[:, 0] * 800 + P[:, 1] * 600, P[:, 2] * 300, 9)
    c = c * (0.95 + 0.10 * (fine - 0.5))[:, None]
    low = np.clip((0.07 - P[:, 2]) / 0.06, 0, 1)
    dirt = (0.25 + 0.75 * fbm(P[:, 0] * 120 + 3, P[:, 1] * 120 + P[:, 2] * 60, 17)) * low * 0.45 * dirt_k
    c = mix(c, c * col((0.66, 0.62, 0.57)), np.clip(dirt, 0, 0.45))           # серая слякоть на лапах
    up = np.clip((N[:, 2] - 0.55) / 0.45, 0, 1)
    sp = (vnoise(P[:, 0] * 520, P[:, 1] * 520 + P[:, 2] * 300, 23) > 0.78).astype(np.float32)
    c = mix(c, col((0.80, 0.83, 0.88)), np.clip(up * 0.22 * sp, 0, 0.22))     # снежинки на спине
    light = 0.92 + 0.16 * np.clip(N[:, 2] * 0.5 + 0.5, 0, 1) + 0.04 * np.clip(-N[:, 1], 0, 1)
    ao = 0.74 + 0.26 * np.clip(P[:, 2] / 0.05, 0, 1)
    belly = 1.0 - 0.14 * np.clip(-N[:, 2] - 0.4, 0, 1)
    return c * (light * ao * belly)[:, None]


def coat(P, N, extra=None):
    m = black_mask(P)
    if extra is not None:
        m = np.maximum(m, extra)
    c = mix(white_coat(P), brindle(P), m)
    pink = np.clip(-N[:, 2] - 0.55, 0, 1) * (1 - m) * 0.6                    # розоватое голое брюхо
    c = mix(c, col((0.80, 0.68, 0.66)), pink)
    return c


def paint_eyes(c, P, N):
    front = N[:, 1] < -0.15
    for ex, ez in EYES:
        d = np.hypot(P[:, 0] - ex, P[:, 2] - ez)
        socket = front & (d < 0.0165)
        c = np.where(socket[:, None], mix(c, col((0.04, 0.035, 0.035)), np.clip((0.0165 - d) / 0.003, 0, 1) * 0.5), c)
        eye = front & (d < 0.0128)
        # правый глаз (−X) косит вверх-внутрь: снизу-снаружи виден белок (фото спереди)
        if ex < 0:
            c = np.where(eye[:, None], col((0.80, 0.77, 0.72)), c)
            ix, iz, ir = ex + 0.0025, ez + 0.0030, 0.0098
        else:
            ix, iz, ir = ex, ez, 0.0108
        di = np.hypot(P[:, 0] - ix, P[:, 2] - iz)
        iris = eye & (di < ir)
        g = np.clip(di / ir, 0, 1)
        ic = mix(col((0.36, 0.21, 0.10)), col((0.14, 0.08, 0.04)), g ** 1.5)    # карий, к краю темнее
        c = np.where(iris[:, None], ic, c)
        c = np.where((eye & (di < 0.0060))[:, None], col((0.02, 0.018, 0.018)), c)
        rim = eye & (d > 0.0123)
        c = np.where(rim[:, None], col((0.03, 0.03, 0.03)), c)
        hl = eye & (np.hypot(P[:, 0] - ix + 0.0035, P[:, 2] - iz - 0.0040) < 0.0030)
        c = np.where(hl[:, None], col((0.92, 0.92, 0.90)), c)
    return c


def paint_head(P, N):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    n = len(P)
    dark = brindle(P)
    # седина: немного везде, больше на щеках, сильно на морде, почти бело-серые брыли
    g = np.full(n, 0.12, np.float32)
    g = np.maximum(g, 0.30 * np.clip((np.abs(N[:, 0]) - 0.4) * 2, 0, 1) * (z < 0.40))
    muzzle = np.clip((-0.262 - y) / 0.012, 0, 1) * np.clip((0.366 - z) / 0.030, 0, 1)
    g = np.maximum(g, 0.65 * muzzle)
    jowl = np.clip((0.335 - z) / 0.025, 0, 1) * np.clip((-0.240 - y) / 0.02, 0, 1)
    g = np.maximum(g, 0.85 * jowl)
    g = np.maximum(g, 0.40 * np.clip((0.372 - z) / 0.02, 0, 1) * np.clip((-x - 0.025) / 0.02, 0, 1)
                   * (N[:, 1] < 0.2))                                         # правая щека седее (фото)
    for ex, ez in EYES:                                                       # вокруг глаз — тёмное кольцо
        g = g * (1 - 0.8 * np.clip((0.022 - np.hypot(x - ex, z - ez)) / 0.006, 0, 1))
    fleck = vnoise(x * 900, z * 900 + y * 600, 91)
    c = mix(dark, col((0.66, 0.65, 0.63)), np.clip(g + (fleck - 0.5) * 0.5 * (g > 0.2), 0, 1))
    # горло и низ затылка — белые (переходят в белую шею)
    throat = np.clip((0.318 - z) / 0.014, 0, 1) * np.clip((y + 0.250) / 0.02, 0, 1)
    c = mix(c, white_coat(P), throat)
    # проточина: белая полоса от затылка по лбу, сужается между глаз и кончается на переносице
    hw = 0.011 + 0.012 * np.clip((z - 0.360) / 0.060, 0, 1)
    hw = np.where(y > -0.215, 0.016 - 0.004 * np.clip((y + 0.215) / 0.025, 0, 1), hw)
    edge = (fbm(x * 260, z * 180 + y * 120, 93) - 0.5) * 0.008
    blaze = np.clip((hw - np.abs(x - 0.002 + edge)) / 0.004, 0, 1) * np.clip((z - 0.350) / 0.008, 0, 1)
    blaze = blaze * (N[:, 1] < 0.45) * np.clip((y + 0.190) / -0.012, 0, 1)
    bw = mix(white_coat(P) * 0.97, col((0.70, 0.69, 0.67)), np.clip((0.362 - z) / 0.010, 0, 1))   # внизу сереет
    c = mix(c, bw, blaze)
    # нос: широкая чёрная мочка с ноздрями и бликом
    front = N[:, 1] < -0.25
    nose = front & (((x / 0.022) ** 2 + ((z - 0.348) / 0.013) ** 2) < 1.0) & (y < -0.290)
    c = np.where(nose[:, None], col((0.045, 0.042, 0.042)), c)
    for sx in (-1, 1):
        nos = nose & (np.hypot(x - 0.0085 * sx, (z - 0.345) * 1.4) < 0.0040)
        c = np.where(nos[:, None], col((0.005, 0.005, 0.005)), c)
    hl = nose & (np.hypot(x + 0.004, z - 0.356) < 0.004)
    c = np.where(hl[:, None], col((0.20, 0.20, 0.21)), c)
    # розовое пятнышко на морде справа от носа (фото спереди)
    pink = front & (np.hypot(x + 0.021, z - 0.336) < 0.0055) & (y < -0.280)
    c = np.where(pink[:, None], col((0.68, 0.55, 0.53)), c)
    # линия рта: опускается к уголкам под брылями и тает к щекам; бороздка под носом; тёмная нижняя губа
    mz = 0.322 - 0.020 * (x / 0.05) ** 2
    lip = front & (z < mz - 0.001) & (z > mz - 0.009) & (np.abs(x) < 0.016)
    c = np.where(lip[:, None], col((0.30, 0.22, 0.22)), c)
    mouth = (front & (np.abs(z - mz) < 0.0022)).astype(np.float32)
    c = mix(c, col((0.05, 0.045, 0.045)), mouth * np.clip((0.050 - np.abs(x)) / 0.012, 0, 1))
    phil = front & (np.abs(x) < 0.0020) & (z > 0.321) & (z < 0.334)
    c = np.where(phil[:, None], col((0.06, 0.055, 0.055)), c)
    c = paint_eyes(c, P, N)
    return c


def paint_ear(tag, P, N, u, v):
    # форма: широкое основание, круглый верх (u — поперёк, v — от основания к кончику)
    e = ((u - 0.5) / 0.50) ** 2 + (np.maximum(v - 0.40, 0) / 0.58) ** 2
    alpha = (e < 1.0).astype(np.float32)
    if tag == "ear_out":
        c = brindle(P) * 1.05
    else:
        skin = col((0.56, 0.43, 0.41)) * (0.90 + 0.16 * vnoise(u * 9, v * 9, 13))[:, None]
        cav = np.clip(1.0 - (((u - 0.5) / 0.34) ** 2 + ((v - 0.45) / 0.40) ** 2), 0, 1)
        c = mix(skin, col((0.42, 0.32, 0.31)), cav * 0.30)
        c = mix(c, brindle(P), np.clip((e - 0.55) * 3.5, 0, 1))                 # тёмный пушистый край
        c = mix(c, brindle(P), np.clip((0.22 - v) / 0.18, 0, 1) * 0.85)         # шерсть у основания
    c = c * (0.92 + 0.12 * v)[:, None]
    return c, alpha


def paint_paw(P, N, u, v):
    c = white_coat(P) * col((0.98, 0.96, 0.94))
    toes = (v > 0.45) & (np.abs(u - 0.5) < 0.30)
    groove = toes & (np.abs(((u - 0.5) * 8.0 + 0.5) % 1.0 - 0.5) > 0.40)
    c = c * np.where(groove, 0.80, 1.0)[:, None]
    c = mix(c, col((0.86, 0.74, 0.72)), 0.25 * toes)                          # розоватые пальцы
    nail = (v > 0.90) & (np.abs(u - 0.5) < 0.30) & (np.abs(((u - 0.5) * 8.0) % 1.0 - 0.5) > 0.15)
    c = np.where(nail[:, None], col((0.86, 0.82, 0.78)), c)
    pad = np.clip(-N[:, 2] - 0.6, 0, 1) * 2
    c = mix(c, col((0.20, 0.17, 0.17)), np.clip(pad, 0, 0.9))                   # тёмные подушечки снизу
    return c


def paint_collar(P, N, u, v):
    base = col((0.88, 0.37, 0.08)) * (0.92 + 0.10 * vnoise(u * 60, v * 4, 101))[:, None]
    edge = np.clip(np.abs(v - 0.5) * 2 - 0.65, 0, 1) * 2.0
    c = base * (1 - 0.35 * edge)[:, None]
    weave = (np.abs(((u * 90.0) % 1.0) - 0.5) > 0.42)
    c = c * np.where(weave, 0.9, 1.0)[:, None]
    light = 0.90 + 0.18 * np.clip(N[:, 2] * 0.5 + 0.5, 0, 1)
    return c * light[:, None]


def paint(tag, refs, P, N, LUV):
    n = len(P); alpha = np.ones(n, np.float32)
    P = inv_head(P) if tag in ("head", "ear_in", "ear_out") else (P if tag == "collar" else inv_body(P))
    u, v = LUV[:, 0], LUV[:, 1]
    if tag == "head":
        c = finish(paint_head(P, N), P, N)
    elif tag in ("body", "neck", "tail", "leg_r"):
        c = finish(coat(P, N), P, N)
    elif tag == "leg_f":
        # правая передняя лапа чёрная до запястья (фото спереди и сбоку)
        right = np.clip(-P[:, 0] / 0.02, 0, 1) * np.clip((P[:, 2] - 0.050) / 0.010, 0, 1)
        c = finish(coat(P, N, right), P, N)
    elif tag == "paw":
        c = finish(paint_paw(P, N, u, v), P, N, dirt_k=0.8)
    elif tag in ("ear_in", "ear_out"):
        c, alpha = paint_ear(tag, P, N, u, v)
    elif tag == "collar":
        c = paint_collar(P, N, u, v)
    else:
        c = np.tile(col((0.03, 0.03, 0.03)), (n, 1))
    return np.clip(c, 0, 1), alpha


# =====================================================================================
#  Атлас, скелет, анимации, экспорт
# =====================================================================================
def save_atlas(rgba):
    if not os.environ.get("PS2_OFF"):
        rgba = M["ps2_module"]().ps2_pass(rgba, TEX_NAME)
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


def rig(ob, used, mb, sc):
    arm_data = bpy.data.armatures.new("HyugaRig")
    arm = bpy.data.objects.new("Hyuga", arm_data)
    sc.collection.objects.link(arm)
    select_only(sc, [arm], arm)
    bpy.ops.object.mode_set(mode='EDIT')
    for n, h, t, p in BONES:
        b = arm_data.edit_bones.new(n)
        b.head, b.tail = BONE_F[n]; b.roll = 0.0
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


def wave(t, period, phase=0.0):
    return math.sin(2 * math.pi * (t / period + phase))


def pose_idle(t, L):
    b = 2 * math.pi
    breath = wave(t, L / 3)                                         # три вдоха за цикл (сопит)
    yaw = 6 * math.sin(b * t / L)
    tilt = 4 * math.sin(b * t / L + 1.3)
    twitch = math.exp(-((t - 2.7) / 0.08) ** 2)                     # дёргает левым ухом
    wag = 14 * math.sin(b * t * 4.0) * (0.5 + 0.5 * math.sin(b * t / L))
    p = {
        "Spine1": [("x", -1.0 * breath)],
        "Spine2": [("x", -1.2 * breath)],
        "Neck": [("x", 0.8 * breath), ("z", yaw * 0.35)],
        "Head": [("z", yaw * 0.65), ("y", tilt)],
        "EarL": [("y", -14 * twitch)],
        "Tail": [("z", wag)],
        "_loc": {"Hips": (0, 0, 0.0015 * breath)},
    }
    return p


def pose_look(t, L):
    # смотрит влево — пауза — вправо — пауза — обратно; уши поворачиваются за звуком
    keys = [(0.0, 0, 0), (0.6, 0, 0), (1.2, 40, 8), (2.0, 40, 6), (2.6, -34, -7), (3.4, -34, -5), (4.0, 0, 0)]
    yaw = tilt = 0.0
    for i in range(len(keys) - 1):
        if keys[i][0] <= t <= keys[i + 1][0]:
            k = smooth((t - keys[i][0]) / (keys[i + 1][0] - keys[i][0]))
            yaw = keys[i][1] + (keys[i + 1][1] - keys[i][1]) * k
            tilt = keys[i][2] + (keys[i + 1][2] - keys[i][2]) * k
            break
    p = pose_idle(t, L)
    p["Spine2"] = p["Spine2"] + [("z", yaw * 0.12)]
    p["Neck"] = [("z", yaw * 0.40), ("x", -3)]
    p["Head"] = [("z", yaw * 0.50), ("y", tilt)]
    p["EarL"] = [("z", yaw * 0.25)]; p["EarR"] = [("z", yaw * 0.25)]
    return p


def pose_sniff(t, L):
    """Опускает морду к земле, водит носом и часто-часто нюхает."""
    down = smooth(t / 0.6) * (1 - smooth((t - 2.4) / 0.6))
    sniff = math.sin(2 * math.pi * t * 6.0) * down
    sweep = 12 * math.sin(2 * math.pi * t / L * 2) * down
    p = pose_idle(t, L)
    p["Spine2"] = [("x", 6 * down)]
    p["Neck"] = [("x", 38 * down), ("z", sweep * 0.5)]
    p["Head"] = [("x", 22 * down + 2.0 * sniff), ("z", sweep * 0.5)]
    p["ShoulderL"] = [("x", -6 * down)]; p["ShoulderR"] = [("x", -6 * down)]
    p["ForearmL"] = [("x", 8 * down)]; p["ForearmR"] = [("x", 8 * down)]
    p["_loc"] = {"Hips": (0, 0, -0.006 * down)}
    return p


WALK_PHASE = {"L": (0.0, 0.5), "R": (0.5, 0.0)}      # рысь: левая передняя в паре с правой задней


def pose_walk(t, L):
    p = {}
    b = 2 * math.pi
    for S_, (pf, pr) in WALK_PHASE.items():
        sf = b * (t / L + pf)
        a = 20 * math.cos(sf); lift = max(0.0, math.sin(sf))
        p["Shoulder" + S_] = [("x", a)]
        p["Forearm" + S_] = [("x", 45 * lift)]
        p["Paw" + S_] = [("x", 30 * lift - 6 * max(0.0, -math.sin(sf)))]
        sr = b * (t / L + pr)
        a = 18 * math.cos(sr); lift = max(0.0, math.sin(sr))
        p["Thigh" + S_] = [("x", a - 8 * lift)]
        p["Shin" + S_] = [("x", 18 * lift)]
        p["Hock" + S_] = [("x", -32 * lift)]
        p["Foot" + S_] = [("x", 18 * lift)]
    bob = math.cos(b * t / L * 2)
    roll = 2.5 * math.sin(b * t / L)
    p["Hips"] = [("y", roll)]
    p["Spine1"] = [("y", -roll * 0.5)]
    p["Neck"] = [("x", 1.5 * bob)]
    p["Head"] = [("x", -1.5 * bob)]
    p["Tail"] = [("z", 10 * math.sin(b * t / L * 2))]
    p["_loc"] = {"Hips": (0, 0, 0.004 * bob)}
    return p


def key_pose(arm, pose, f):
    loc = pose.pop("_loc", {})
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = qw(arm, pb.name, pose.get(pb.name, []))
        pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
    hb = arm.pose.bones["Hips"]
    rq = arm.data.bones["Hips"].matrix_local.to_quaternion()
    hb.location = rq.inverted() @ Vector(loc.get("Hips", (0, 0, 0)))
    hb.keyframe_insert("location", frame=f, group="Hips")


def make_anim(arm, name, L, fn, step=2):
    ac = M["new_action"](arm, name)
    N = int(round(L * FPS))
    for f in range(0, N + 1, step):
        key_pose(arm, fn(f / FPS if f < N else 0.0, L), f)
    M["push_nla"](arm, ac, name)
    return {"frames": N + 1, "len_s": L}


def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion(); pb.location = (0, 0, 0)


def export_gltf(sc, arm, body):
    select_only(sc, [arm, body], arm)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(ROOT, "assets", "models", "hyuga.gltf"), use_selection=True, use_active_scene=True,
        export_format='GLTF_SEPARATE', export_keep_originals=True, export_apply=False, export_skins=True,
        export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
        export_frame_step=1, export_optimize_animation_size=True, export_anim_single_armature=True,
        export_def_bones=False, export_reset_pose_bones=True, export_bake_animation=False)


PREVIEW_VIEWS = [  # имя, направление на камеру — как ракурсы фото
    ("side_right", (-1, 0, 0.05)), ("side_left", (1, 0, 0.05)), ("front", (0, -1, 0.05)),
    ("photo_front", (0.25, -1, 1.1)), ("photo_back", (-0.35, 1, 1.4)), ("q34", (0.7, -1, 0.35)),
]


def preview(sc, body, views=PREVIEW_VIEWS):
    """Превью в нескольких ракурсах — для сравнения с фото."""
    if not PREVIEW:
        return
    os.makedirs(PREVIEW, exist_ok=True)
    keep = (sc.render.engine, sc.camera)
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'FLAT'; sc.display.shading.color_type = 'TEXTURE'
    sc.render.resolution_x, sc.render.resolution_y = 600, 600
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    w = bpy.data.worlds.get("HyugaPreview") or bpy.data.worlds.new("HyugaPreview")
    w.color = (0.32, 0.32, 0.32); sc.world = w
    cam_d = bpy.data.cameras.new("HyugaPrevCam"); cam_d.type = 'ORTHO'; cam_d.ortho_scale = 0.66
    cam = bpy.data.objects.new("HyugaPrevCam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
    for tag, d in views:
        d = Vector(d).normalized()
        cam.location = Vector((0.0, 0.0, 0.25)) + d * 3
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(PREVIEW, "hyuga_%s.png" % tag)
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True); bpy.data.cameras.remove(cam_d)
    sc.render.engine = keep[0]; sc.camera = keep[1]


def scene_extras(sc):
    cam_d = bpy.data.cameras.get("HyugaCamera") or bpy.data.cameras.new("HyugaCamera")
    cam_d.lens = 60.0
    cam = bpy.data.objects.new("HyugaCamera", cam_d); sc.collection.objects.link(cam)
    target = Vector((0.0, 0.0, 0.25)); d = Vector((-0.75, -0.75, 0.30)).normalized()
    cam.location = target + d * 1.7
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    sun_d = bpy.data.lights.get("HyugaSun") or bpy.data.lights.new("HyugaSun", 'SUN')
    sun = bpy.data.objects.new("HyugaSun", sun_d); sc.collection.objects.link(sun)
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
            if d.users == 0 and d.name.startswith("Hyuga"):
                blk.remove(d)
    sc.render.fps = FPS; sc.render.fps_base = 1.0

    Y["ATLAS"] = ATLAS
    dens = {"head": 3.2, "body": 1.0, "neck": 1.2, "collar": 0.9, "tail": 0.9}
    for S_ in "LR":
        dens.update({"ear%s_in" % S_: 1.6, "ear%s_out" % S_: 1.1, "f_paw" + S_: 1.4, "r_paw" + S_: 1.3})
    Y["ISL_DENS"] = dens
    Y["paint"] = paint
    mb = build_all()
    D, pos = Y["pack_islands"](mb, size=ATLAS, pad=2)
    img = bpy.data.images.get(TEX_NAME)
    mats = [Y["make_material"]("HyugaFur", img, False), Y["make_material"]("HyugaEar", img, True)]
    body, fsel, used = Y["make_object"](mb, 0, "HyugaMesh", sc.collection, mats)
    info = {"tris": sum(len(mb.faces[f]) - 2 for f in fsel), "verts": len(used), "atlas": ATLAS,
            "density_px_per_m": round(D, 1)}

    rgba, Tb = Y["bake_atlas"](mb, {0: (body.data, fsel)}, {})
    img = save_atlas(rgba)
    for m, a in zip(mats, (False, True)):
        Y["make_material"](m.name, img, a)
    info["atlas_fill"] = round(float((Tb >= 0).mean()), 3)

    arm = rig(body, used, mb, sc)
    select_only(sc, [arm], arm)
    bpy.ops.object.mode_set(mode='POSE')
    info["anims"] = {
        "Idle": make_anim(arm, "Idle", 4.0, pose_idle),
        "Walk": make_anim(arm, "Walk", 0.8, pose_walk, step=1),
        "Sniff": make_anim(arm, "Sniff", 3.0, pose_sniff),
        "LookAround": make_anim(arm, "LookAround", 4.0, pose_look),
    }
    reset_pose(arm)
    bpy.ops.object.mode_set(mode='OBJECT')
    export_gltf(sc, arm, body)
    preview(sc, body)
    scene_extras(sc)
    ad = arm.animation_data
    ad.action = bpy.data.actions.get("Idle")
    sc.frame_start, sc.frame_end = 0, int(4.0 * FPS)
    select_only(sc, [arm], arm)
    info["bones"] = len(BONES)
    print("BUILD_HYUGA " + json.dumps(info))
    return info


result = main()
