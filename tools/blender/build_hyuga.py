# -*- coding: utf-8 -*-
# Хьюга (YUR-22): пегий французский бульдог, low-poly модель в стиле PS2 по фото docs/references/hyuga/hyuga_photo_*.png
#   side  — правый бок (чёрное седло на плече и правой передней лапе, пятно на середине спины, пятно на крупе);
#   back  — сверху-сзади (три пятна по хребту, белая шея, оранжевый ошейник);
#   front — спереди-сверху (тёмная тигровая голова с белой проточиной, седая морда, розовое пятнышко у носа).
#
# Устроено так же, как макака (tools/blender/build_monkey.py) и Юрчик (build_yurchik_v3.py) — помощники берутся оттуда:
#   1. Геометрия — «кольца»-сечения, соединённые в трубы: туловище — 17 колец по гладкой кривой через опорные
#      сечения (+ бугры лопаток и бёдер), голова — 16 горизонтальных колец по 20 точек, морда/брыли/щёки/надбровья —
#      плавные «бугры» (head_pt); шея, ошейник и хвостик — трубы; каждая лапа — одна труба от лопатки (таза) до
#      запястья (плюсны) плюс круглая лапка с плоской подошвой. Уши-«летучая мышь» — две изогнутые пластинки
#      (внутренняя и наружная сторона), форма вырезается альфой.
#   2. Развёртка — прямоугольные островки, упакованные в один атлас 512×512.
#   3. Текстура — процедурная (ортогонального концепта нет, только фото): белая шерсть, чёрные тигровые пятна
#      заданы 3D-эллипсоидами по фото, голова, глаза, нос, проточина, ошейник. В текстуру запечены мягкий свет
#      и затенение (AO: лучи из каждой вершины по полусфере) — отсюда объём.
#   Сравнение с фото под теми же ракурсами — tools/blender/hyuga_compare.py.
#   4. Скелет — свой: таз, 2 позвонка, шея, голова, уши, хвост; передние лапы по 3 кости, задние по 4. Поза покоя — стоит.
#      Листовые кости: Chest/Belly (масштаб раздувает бока при дыхании), LidL/LidR (закрытые веки — в покое
#      утоплены в голову, во сне выдвигаются на глаза).
#   5. Анимации — процедурные ключи: Idle (4 с), Walk (рысь на месте, 0.8 с), Sniff (нюхает землю, 3 с),
#      LookAround (4 с), Sleep (спит клубком на боку и дышит, 4.5 с, референс hyuga_sleep_ref.webp). Все зациклены.
#      Добавочные (только отклонение от покоя, для наложения поверх Sleep): SleepTwitchEar, SleepTwitchPaw, SleepSigh.
#      В игре: scripts/world/hyuga_sleep.gd (диван в scenes/levels/stairwell.tscn).
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
ATLAS = 512
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
    ("Shoulder", (0.072, -0.104, 0.200), (0.085, -0.112, 0.116), "Spine2"),
    ("Forearm", (0.085, -0.112, 0.116), (0.082, -0.114, 0.030), "Shoulder"),
    ("Paw", (0.082, -0.114, 0.030), (0.089, -0.148, 0.010), "Forearm"),
    ("Thigh", (0.060, 0.148, 0.224), (0.079, 0.131, 0.124), "Hips"),
    ("Shin", (0.079, 0.131, 0.124), (0.074, 0.158, 0.068), "Thigh"),
    ("Hock", (0.074, 0.158, 0.068), (0.071, 0.160, 0.022), "Shin"),
    ("Foot", (0.071, 0.160, 0.022), (0.071, 0.126, 0.010), "Hock"),
    ("Ear", (0.052, -0.198, 0.414), (0.090, -0.196, 0.505), "Head"),
    ("Lid", (0.048, -0.262, 0.374), (0.048, -0.290, 0.374), "Head"),    # веко: в покое спрятано в голове
]
BONES = [
    ("Hips", (0, 0.140, 0.238), (0, 0.040, 0.238), None),
    ("Spine1", (0, 0.040, 0.238), (0, -0.060, 0.232), "Hips"),
    ("Spine2", (0, -0.060, 0.232), (0, -0.112, 0.240), "Spine1"),
    ("Neck", (0, -0.112, 0.258), (0, -0.178, 0.338), "Spine2"),
    ("Head", (0, -0.178, 0.338), (0, -0.205, 0.450), "Neck"),
    ("Tail", (0, 0.210, 0.250), (0, 0.229, 0.224), "Hips"),
    # дыхание: листовые кости в середине груди и живота — их масштаб раздувает бока и брюхо (хребет не трогают)
    ("Chest", (0, -0.075, 0.212), (0, -0.125, 0.212), "Spine2"),
    ("Belly", (0, 0.045, 0.214), (0, -0.005, 0.214), "Spine1"),
]
LEG_DX = {"Shoulder": 0.008, "Forearm": 0.008, "Paw": 0.008, "Thigh": 0.006, "Shin": 0.006, "Hock": 0.006,
          "Foot": 0.006}                                      # лапы чуть шире груди (широкая постановка)
for _n, _h, _t, _p in LEFT_BONES:
    _dx = LEG_DX.get(_n, 0.0)
    for _sx, _suf in ((1, "L"), (-1, "R")):
        BONES.append((_n + _suf, ((_h[0] + _dx) * _sx, _h[1], _h[2]), ((_t[0] + _dx) * _sx, _t[1], _t[2]),
                      _p if _p in ("Spine2", "Hips", "Head") else _p + _suf))
BONE = {n: (Vector(h), Vector(t)) for n, h, t, p in BONES}

# Части строятся в «чертёжных» координатах (как размечено выше), затем приводятся к пропорциям бульдога
# (замер по фото сбоку: длина корпуса к высоте ≈ 1.4): корпус вытянут по длине (SY), голова увеличена и опущена
# к груди на короткую шею. Лапы не растягиваются — только переезжают вместе с плечом/тазом (LEG_Y).
# Шея с ошейником строятся сразу в итоговых координатах — между корпусом и головой.
SY = 1.15
HEAD_PIVOT = Vector((0, -0.180, 0.335))
HEAD_S = 1.12
HEAD_T = Vector((0, -0.010, -0.050))
LEG_Y = {"f": -0.105, "r": 0.150}                       # где лапа крепится к корпусу (по длине)
FRONT_LEG, REAR_LEG = ("Shoulder", "Forearm", "Paw"), ("Thigh", "Shin", "Hock", "Foot")


def leg_shift(k):
    return Vector((0, LEG_Y[k] * (SY - 1), 0))


def xf_body(p):
    return Vector((p[0], p[1] * SY, p[2]))


def xf_head(p):
    return HEAD_PIVOT + (Vector(p) - HEAD_PIVOT) * HEAD_S + HEAD_T


def xf_legf(p):
    return Vector(p) + leg_shift("f")


def xf_legr(p):
    return Vector(p) + leg_shift("r")


def inv_body(P):
    return P * np.array([1, 1 / SY, 1], np.float32)


def inv_head(P):
    pv, t = np.array(HEAD_PIVOT, np.float32), np.array(HEAD_T, np.float32)
    return (P - pv - t) / HEAD_S + pv


def inv_leg(P, k):
    return P - np.array(leg_shift(k), np.float32)


def bone_final(n, h, t):
    if n == "Head" or n.startswith("Ear") or n.startswith("Lid"):
        return xf_head(h), xf_head(t)
    if n == "Neck":
        return xf_body(h), xf_head(t)
    base = n[:-1] if n[-1:] in ("L", "R") else n
    if base in FRONT_LEG:
        return xf_legf(h), xf_legf(t)
    if base in REAR_LEG:
        return xf_legr(h), xf_legr(t)
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


def gauss(x, c, s):
    return math.exp(-((x - c) / s) ** 2)


def catmull(rows, n):
    """Гладкая кривая Катмулла-Рома через строки таблицы → n равномерных по индексу выборок."""
    R = [list(r) for r in rows]
    out = []
    for k in range(n):
        t = k * (len(R) - 1) / (n - 1)
        i = min(int(t), len(R) - 2); f = t - i
        p0, p1, p2, p3 = R[max(i - 1, 0)], R[i], R[i + 1], R[min(i + 2, len(R) - 1)]
        out.append(tuple(0.5 * (2 * b + (-a + c) * f + (2 * a - 5 * b + 4 * c - d) * f * f
                                + (-a + 3 * b - 3 * c + d) * f ** 3) for a, b, c, d in zip(p0, p1, p2, p3)))
    return out


# =====================================================================================
#  Геометрия
# =====================================================================================
# Туловище: сечения поперёк спины (y, центр z, полуширина, вверх, вниз) — опорные; между ними гладкая кривая.
# Грудь широкая и глубокая, живот поджат к паху, над поясницей лёгкий «горбик», круп круглый.
T_ST = [
    (-0.172, 0.195, 0.078, 0.046, 0.082), (-0.160, 0.200, 0.100, 0.062, 0.104), (-0.122, 0.214, 0.110, 0.086, 0.118),
    (-0.078, 0.220, 0.122, 0.088, 0.120), (-0.028, 0.225, 0.124, 0.080, 0.106), (0.022, 0.232, 0.114, 0.068, 0.098),
    (0.072, 0.237, 0.100, 0.064, 0.090), (0.118, 0.238, 0.094, 0.066, 0.082), (0.158, 0.237, 0.090, 0.062, 0.074),
    (0.190, 0.236, 0.078, 0.056, 0.066), (0.208, 0.234, 0.058, 0.044, 0.052), (0.218, 0.232, 0.030, 0.024, 0.030),
]
T_FRONT, T_REAR = (0, -0.178, 0.188), (0, 0.223, 0.232)
T_STATIONS = 17
T_COLS = 16
T_EXP = 2.2

# Голова: горизонтальные сечения (z, полуширина, затылок Y, лицо Y) — опорные; кольца берутся на высотах H_ZS.
# Подбородок z≈0.286, макушка z≈0.453. Морда, брыли, щёки, надбровья и переносица — плавные «бугры» (head_pt).
H_CTRL = np.array([
    (0.288, 0.046, -0.196, -0.268), (0.300, 0.068, -0.174, -0.276), (0.315, 0.078, -0.160, -0.276),
    (0.330, 0.082, -0.152, -0.278), (0.345, 0.081, -0.148, -0.276), (0.360, 0.079, -0.146, -0.270),
    (0.375, 0.078, -0.147, -0.266), (0.390, 0.076, -0.149, -0.264), (0.405, 0.072, -0.152, -0.260),
    (0.420, 0.066, -0.156, -0.254), (0.435, 0.056, -0.163, -0.244), (0.446, 0.042, -0.174, -0.232),
    (0.452, 0.030, -0.188, -0.218),
])
H_ZS = [0.290, 0.300, 0.310, 0.320, 0.330, 0.340, 0.350, 0.360, 0.370, 0.382, 0.395, 0.408, 0.421, 0.433, 0.443, 0.450]
H_COLS = 20
EYES = [(-0.048, 0.374), (0.048, 0.374)]          # центры глаз (x, z): широко, в передних углах черепа
NECK = [xf_body((0, -0.100, 0.248)), xf_head((0, -0.200, 0.372))]   # итоговые координаты
NECK_R = [(0.082, 0.076), (0.078, 0.058)]          # (бок, вперёд) внизу и вверху шеи: короткая и толстая
NECK_SIDES = 12


def torso_ring(y, zc, a, rt, rb):
    e = 2.0 / T_EXP
    pts = []
    for k in range(T_COLS):
        th = 2 * math.pi * k / T_COLS                         # 0 — спина, 90° — левый бок (+X)
        s, c = math.sin(th), math.cos(th)
        x, z = a * sgnpow(s, e), zc + (rt if c >= 0 else rb) * sgnpow(c, e)
        at = abs(math.atan2(s, c))                            # 0 — хребет, π — брюхо
        bump = (0.010 * gauss(y, -0.100, 0.035) * gauss(at, 1.22, 0.45)      # лопатки
                + 0.006 * gauss(y, 0.150, 0.040) * gauss(at, 1.75, 0.50)     # бёдра
                - 0.003 * gauss(at, 0.0, 0.25) * (1.0 if -0.08 < y < 0.12 else 0.0))   # ложбинка хребта
        L = math.hypot(x, z - zc) or 1.0
        pts.append((x + x / L * bump, y, z + (z - zc) / L * bump))
    return pts


def build_torso(mb):
    w = wfn(["Hips", "Spine1", "Spine2"])
    rings = [[mb.vert(T_FRONT, w(T_FRONT))] * T_COLS]
    for st in catmull(T_ST, T_STATIONS):
        pts = torso_ring(*st)
        rings.append(mb.ring(pts, [w(p) for p in pts]))
    rear = mb.vert(T_REAR, w(T_REAR))
    loft(mb, rings, "body", "body", seam=T_COLS // 2, pole=rear)


def neck_at(t):
    p = NECK[0].lerp(NECK[1], t)
    r0, r1 = NECK_R
    return p, (r0[0] + (r1[0] - r0[0]) * t, r0[1] + (r1[1] - r0[1]) * t)


def neck_w(p):
    """Веса шеи и ошейника — по положению вдоль оси шеи (а не по расстоянию до костей): кольцо гнётся целиком,
    ошейник не «встаёт гребнем», когда голова опускается."""
    d = NECK[1] - NECK[0]
    t = max(0.0, min(1.0, (Vector(p) - NECK[0]).dot(d) / d.length_squared))
    if t < 0.5:
        k = smooth(t / 0.5)
        return {n: x for n, x in (("Spine2", 1 - k), ("Neck", k)) if x > 0.02}
    k = smooth((t - 0.5) / 0.5)
    return {n: x for n, x in (("Neck", 1 - k), ("Head", k)) if x > 0.02}


def build_neck(mb):
    w = neck_w
    ts = [0.0, 0.33, 0.67, 1.0]
    path = [neck_at(t)[0] for t in ts]; radii = [neck_at(t)[1] for t in ts]
    tube(mb, path, radii, NECK_SIDES, "neck", "neck", w, cap_end=0, ref=(0, -1, 0))


def build_collar(mb):
    """Оранжевый ошейник: кольцо чуть шире шеи, те же сечения, что у шеи (кадр трубы совпадает)."""
    w = neck_w
    ts = [0.30, 0.36, 0.42]
    path, radii = [], []
    for t, grow in zip(ts, (0.0035, 0.0055, 0.0035)):
        p, (rs, ru) = neck_at(t)
        path.append(p); radii.append((rs + grow, ru + grow))
    # шея — прямая, поэтому рамка tube() (от ref) везде одна и та же: вершины ошейника стоят ровно над вершинами шеи
    tube(mb, path, radii, NECK_SIDES, "collar", "collar", w, cap_end=0, ref=(0, -1, 0))


def head_pt(z, th):
    """Точка головы на высоте z, угол th (0 — лицо, 90° — левая щека)."""
    a = float(np.interp(z, H_CTRL[:, 0], H_CTRL[:, 1]))
    yb = float(np.interp(z, H_CTRL[:, 0], H_CTRL[:, 2])); yf = float(np.interp(z, H_CTRL[:, 0], H_CTRL[:, 3]))
    yc, d = (yb + yf) / 2, (yb - yf) / 2
    front = math.cos(th) > 0
    x, y = sellipse(a, d, d, yc, th, 2.25 if front else 2.0)
    at = abs(math.atan2(math.sin(th), math.cos(th)))          # 0 — лицо, π — затылок
    sx = 1.0 if x >= 0 else -1.0
    plateau = smooth((z - 0.298) / 0.024) * (1 - smooth((z - 0.352) / 0.016))
    y -= 0.015 * plateau * math.exp(-(at / 0.62) ** 4)                       # морда: короткий плоский «кирпичик»
    y -= 0.008 * gauss(z, 0.365, 0.006) * math.exp(-(at / 0.45) ** 2)        # складка (валик) над носом
    y += 0.006 * gauss(z, 0.374, 0.007) * math.exp(-(at / 0.30) ** 2)        # переносица (стоп) вдавлена
    y -= 0.005 * gauss(z, 0.392, 0.008) * gauss(at, 0.45, 0.25)              # надбровья
    jw = gauss(z, 0.312, 0.016) * gauss(at, 0.60, 0.40)                      # брыли тяжело свисают вниз-наружу
    x += sx * 0.015 * jw; y -= 0.010 * jw; zz = z - 0.022 * jw
    y -= 0.008 * gauss(z, 0.300, 0.010) * math.exp(-(at / 0.55) ** 2)        # нижняя челюсть чуть вперёд
    x += sx * 0.011 * gauss(z, 0.348, 0.022) * gauss(at, 1.30, 0.45)        # щёки
    if front:
        for ex, ez in EYES:                                                   # глаза навыкате
            y -= 0.0035 * math.exp(-((x - ex) ** 2 + (z - ez) ** 2) / 0.011 ** 2)
    return (x, y, zz)


def build_head(mb):
    w = {"Head": 1.0}
    rings = [[mb.vert((0, -0.226, 0.286), w)] * H_COLS]
    for z in H_ZS:
        rings.append(mb.ring([head_pt(z, 2 * math.pi * k / H_COLS) for k in range(H_COLS)], w))
    top = mb.vert((0, -0.203, 0.4535), w)
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
    W, H = 0.058, 0.108
    base = Vector((0.052 * sx, -0.198, 0.414))
    w = wfn(["Head", "Ear" + S_])
    for layer, off, tag in (("in", 0.0, "ear_in"), ("out", -0.0035, "ear_out")):
        rows = []
        for j in range(6):
            v = j / 5
            row = []
            for i in range(5):
                u = i / 4 - 0.5
                cup = -0.013 * (1 - (2 * u) ** 2) * math.sin(math.pi * min(v * 1.1, 1.0))   # раковина: середина вглубь
                roll = 0.004 * (2 * u) ** 2 * v                                                 # края завёрнуты вперёд
                taper = 1.0 - 0.08 * v                                                          # к верху чуть уже
                p = base + side * (u * W * taper) + up * (v * H - 0.012) + nrm * (cup + roll + off)
                row.append(p)
            rows.append(mb.ring(row, [w(p) for p in row]))
        d = nrm if layer == "in" else -nrm
        loft(mb, rows, "ear%s_%s" % (S_, layer), tag, closed=False, mat=1, direction=d)


LID_R = (0.0195, 0.0175)     # полуоси века (поперёк, вверх): закрывает глаз вместе с тёмным ободком
LID_IN = 0.016               # насколько веко утоплено в голову в покое (по нормали глаза, чертёжные метры)


def head_th(z, x):
    """Угол сечения головы на высоте z, при котором точка лица имеет абсциссу x (лицевая сторона)."""
    lo, hi = 0.0, math.radians(85) * (1 if x >= 0 else -1)
    for _ in range(40):
        mid = (lo + hi) / 2
        if (head_pt(z, mid)[0] < x) == (x >= 0):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def eye_frame(ex, ez):
    """Центр глаза на поверхности головы и наружная нормаль (чертёжные координаты)."""
    th = head_th(ez, ex)
    c = Vector(head_pt(ez, th))
    du = Vector(head_pt(ez, th + 0.02)) - Vector(head_pt(ez, th - 0.02))
    dv = Vector(head_pt(ez + 0.002, th)) - Vector(head_pt(ez - 0.002, th))
    n = du.cross(dv).normalized()
    if n.y > 0:
        n = -n
    return c, n


def build_lid(mb, sx):
    """Закрытое веко: выпуклая пластинка поверх глаза (повторяет поверхность головы, в середине чуть выпуклее).
    Строится на месте — так запекаются цвет и AO, потом (lids_hide) утапливается в голову; в позе сна
    кость LidL/LidR выдвигает его обратно."""
    S_ = "L" if sx > 0 else "R"
    ex, ez = EYES[0 if sx < 0 else 1]
    c, n = eye_frame(ex, ez)
    w = {"Lid" + S_: 1.0}
    rows = []
    NU, NV = 7, 7
    for j in range(NV):
        v = (j / (NV - 1)) * 2 - 1
        z = ez + v * LID_R[1] * 1.08
        row = []
        for i in range(NU):
            u = (i / (NU - 1)) * 2 - 1
            x = ex + u * LID_R[0] * 1.08 * sx
            p = Vector(head_pt(z, head_th(z, x)))
            dome = max(0.0, 1 - u * u - v * v)
            row.append(p + n * (0.0014 + 0.0022 * dome))
        rows.append(mb.ring(row, w))
    loft(mb, rows, "lid" + S_, "lid", closed=False, mat=1, direction=n)


def flat_sole(mb, a, z0=0.003):
    """Подошва лапы — плоская (вершины ниже z0 прижимаются к полу)."""
    for i in range(a, len(mb.co)):
        if mb.co[i].z < z0:
            mb.co[i] = Vector((mb.co[i].x, mb.co[i].y, z0))


def build_front_leg(mb, sx):
    """Передняя лапа одной трубой от лопатки до запястья (без щелей в суставах) + круглая лапка."""
    S_ = "L" if sx > 0 else "R"
    m = lambda pts: [((p[0] + LEG_DX["Shoulder"]) * sx, p[1], p[2]) for p in pts]
    tube(mb, m([(0.060, -0.098, 0.240), (0.071, -0.106, 0.192), (0.080, -0.111, 0.150), (0.085, -0.112, 0.116),
                (0.084, -0.114, 0.084), (0.083, -0.115, 0.054), (0.082, -0.114, 0.032)]),
         [(0.040, 0.052), (0.040, 0.048), (0.034, 0.038), (0.030, 0.032), (0.027, 0.028), (0.025, 0.026),
          (0.024, 0.024)], 8, "f_leg" + S_, "leg_f",
         wfn(["Spine2", "Shoulder" + S_, "Forearm" + S_, "Paw" + S_]), cap_end=0, ref=(0, -1, 0))
    a = len(mb.co)
    tube(mb, m([(0.082, -0.098, 0.019), (0.083, -0.110, 0.022), (0.086, -0.128, 0.020), (0.089, -0.146, 0.013)]),
         [(0.021, 0.016), (0.025, 0.020), (0.026, 0.017), (0.021, 0.011)], 10, "f_paw" + S_, "paw",
         wfn(["Forearm" + S_, "Paw" + S_]), cap_end=0.8, cap_start=0.6)
    flat_sole(mb, a)


def build_rear_leg(mb, sx):
    """Задняя лапа одной трубой: мощное бедро → колено → голень → скакательный сустав → плюсна; + лапка."""
    S_ = "L" if sx > 0 else "R"
    m = lambda pts: [((p[0] + LEG_DX["Thigh"]) * sx, p[1], p[2]) for p in pts]
    tube(mb, m([(0.056, 0.152, 0.238), (0.064, 0.143, 0.198), (0.072, 0.132, 0.162), (0.077, 0.130, 0.138),
                (0.079, 0.132, 0.118), (0.077, 0.136, 0.098), (0.075, 0.150, 0.078), (0.073, 0.158, 0.056),
                (0.072, 0.160, 0.038), (0.071, 0.160, 0.024)]),
         [(0.045, 0.060), (0.048, 0.066), (0.048, 0.058), (0.044, 0.054), (0.039, 0.047), (0.035, 0.041),
          (0.030, 0.034), (0.026, 0.028), (0.023, 0.023), (0.021, 0.021)], 8, "r_leg" + S_, "leg_r",
         wfn(["Hips", "Thigh" + S_, "Shin" + S_, "Hock" + S_, "Foot" + S_]), cap_end=0, ref=(0, -1, 0))
    a = len(mb.co)
    tube(mb, m([(0.071, 0.170, 0.019), (0.071, 0.158, 0.021), (0.071, 0.141, 0.019), (0.071, 0.126, 0.012)]),
         [(0.020, 0.016), (0.024, 0.019), (0.025, 0.016), (0.020, 0.010)], 10, "r_paw" + S_, "paw",
         wfn(["Hock" + S_, "Foot" + S_]), cap_end=0.8, cap_start=0.6)
    flat_sole(mb, a)


def build_tail(mb):
    tube(mb, [(0, 0.210, 0.250), (0, 0.222, 0.240), (0, 0.228, 0.228)], [0.017, 0.014, 0.009], 8,
         "tail", "tail", wfn(["Hips", "Tail"]), cap_end=1.0)


def build_all():
    mb = MB()
    parts = []                                              # (начало, конец, преобразование) по вершинам

    def part(fn, xf):
        a = len(mb.co); fn(); parts.append((a, len(mb.co), xf))
    part(lambda: build_torso(mb), xf_body)
    part(lambda: (build_neck(mb), build_collar(mb)), None)
    part(lambda: (build_head(mb), build_ear(mb, 1), build_ear(mb, -1), build_lid(mb, 1), build_lid(mb, -1)), xf_head)
    part(lambda: (build_front_leg(mb, 1), build_front_leg(mb, -1)), xf_legf)
    part(lambda: (build_rear_leg(mb, 1), build_rear_leg(mb, -1)), xf_legr)
    part(lambda: build_tail(mb), xf_body)
    for a, b, xf in parts:
        if xf:
            for i in range(a, b):
                mb.co[i] = xf(mb.co[i])
    return mb


# =====================================================================================
#  Запечённое затенение (AO): лучи из каждой вершины по полусфере, препятствия — сама собака и пол
# =====================================================================================
def vertex_ao(mb, me, fsel, used, rays=48, maxd=0.10):
    from mathutils.bvhtree import BVHTree
    verts = [tuple(c) for c in mb.co]
    polys = [mb.faces[f] for f in fsel if not str(mb.ftag[f]).startswith(("ear", "lid"))]
    g = len(verts)
    verts += [(-2, -2, 0), (2, -2, 0), (2, 2, 0), (-2, 2, 0)]
    polys.append((g, g + 1, g + 2, g + 3))
    bvh = BVHTree.FromPolygons(verts, polys)
    dirs = []
    for i in range(rays):                                   # косинусное распределение (спираль Фибоначчи)
        u = (i + 0.5) / rays; ph = i * 2.399963
        r = math.sqrt(u); dirs.append((r * math.cos(ph), r * math.sin(ph), math.sqrt(1 - u)))
    aov = np.ones(len(mb.co), np.float32)
    for k, vid in enumerate(used):
        n = me.vertices[k].normal.normalized()
        t = n.orthogonal().normalized(); b = n.cross(t)
        o = mb.co[vid] + n * 0.003
        occ = 0.0
        for dx, dy, dz in dirs:
            hit = bvh.ray_cast(o, t * dx + b * dy + n * dz, maxd)
            if hit[0] is not None:
                occ += 1.0 - hit[3] / maxd
        aov[vid] = max(0.25, 1.0 - occ / rays)
    return aov


# =====================================================================================
#  Раскраска (процедурная, по фото)
# =====================================================================================
WHITE = (0.92, 0.91, 0.88)
BLACK = (0.095, 0.090, 0.088)
# чёрные пятна: (центр, полуоси) — эллипсоиды в метрах; правый бок — −X
PATCHES = [   # замерено по фото сбоку и сверху-сзади (чертёжные координаты)
    ((-0.032, -0.018, 0.265), (0.085, 0.040, 0.070)),    # седло: верх начинается позади шеи, чуть заходит влево
    ((-0.082, -0.038, 0.200), (0.075, 0.054, 0.110)),    # …спускается по правому боку до брюха
    ((-0.092, -0.095, 0.185), (0.064, 0.055, 0.105)),    # …и вперёд по плечу — в чёрную лапу
    ((0.026, -0.002, 0.290), (0.040, 0.022, 0.030)),     # «рукав» седла через хребет влево — по его заднему краю
    ((-0.006, 0.076, 0.292), (0.084, 0.046, 0.068)),     # круглое пятно посередине спины, по хребту
    ((0.000, 0.168, 0.260), (0.114, 0.066, 0.100)),      # круп; хвостик и задняя сторона бёдер белые
]
_AO = None          # затенение по текселям (bake_atlas_ao кладёт сюда массив перед раскраской каждого тега)
KEY = np.array((0.30, -0.42, 0.86), np.float32); KEY /= np.linalg.norm(KEY)   # запечённый «ключевой» свет


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
    k = np.clip((streak - 0.45) * 1.6, 0, 0.55) * 0.8 + np.clip((fleck - 0.80) * 2.5, 0, 0.35)
    return mix(np.tile(col(BLACK), (len(P), 1)), col((0.38, 0.35, 0.32)), k)


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
    return c * shade(P, N)[:, None]


def shade(P, N):
    """Объём: мягкий свет сверху-спереди-слева + запечённое затенение (AO) по складкам, под брюхом и у пола."""
    ndl = np.clip(N @ KEY * 0.5 + 0.5, 0, 1)
    light = 0.70 + 0.36 * ndl ** 1.3
    sky = 0.96 + 0.05 * N[:, 2]
    ao = 0.55 + 0.45 * _AO if _AO is not None else 0.74 + 0.26 * np.clip(P[:, 2] / 0.05, 0, 1)
    belly = 1.0 - 0.10 * np.clip(-N[:, 2] - 0.4, 0, 1)
    return light * sky * ao * belly


def coat(P, N, extra=None):
    m = black_mask(P)
    m = m * (1 - np.clip((P[:, 1] - 0.200) / 0.012, 0, 1) * np.clip((0.248 - P[:, 2]) / 0.015, 0, 1))   # под хвостом
    if extra is not None:
        m = np.maximum(m, extra)
    c = mix(white_coat(P), brindle(P), m)
    pink = np.clip(-N[:, 2] - 0.55, 0, 1) * (1 - m) * 0.6                    # розоватое голое брюхо
    c = mix(c, col((0.80, 0.68, 0.66)), pink)
    return c


def paint_eyes(c, P, N):
    front = N[:, 1] < -0.05
    for ex, ez in EYES:
        d = np.hypot(P[:, 0] - ex, P[:, 2] - ez)
        socket = front & (d < 0.0182)
        c = np.where(socket[:, None], mix(c, col((0.04, 0.035, 0.035)), np.clip((0.0182 - d) / 0.003, 0, 1) * 0.5), c)
        eye = front & (d < 0.0144)
        # правый глаз (−X) косит вверх-внутрь: снизу-снаружи виден белок (фото спереди)
        if ex < 0:
            c = np.where(eye[:, None], col((0.84, 0.76, 0.72)), c)
            ix, iz, ir = ex + 0.0008, ez + 0.0042, 0.0130
        else:
            ix, iz, ir = ex, ez, 0.0122
        di = np.hypot(P[:, 0] - ix, P[:, 2] - iz)
        iris = eye & (di < ir)
        g = np.clip(di / ir, 0, 1)
        ic = mix(col((0.32, 0.19, 0.09)), col((0.10, 0.06, 0.035)), g ** 1.5)    # карий, к краю темнее
        c = np.where(iris[:, None], ic, c)
        c = np.where((eye & (di < 0.0080))[:, None], col((0.02, 0.018, 0.018)), c)
        rim = eye & (d > 0.0139)
        c = np.where(rim[:, None], col((0.03, 0.03, 0.03)), c)
        hl = eye & (np.hypot(P[:, 0] - ix + 0.0035, P[:, 2] - iz - 0.0040) < 0.0030)
        c = np.where(hl[:, None], col((0.92, 0.92, 0.90)), c)
    return c


def paint_head(P, N):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    n = len(P)
    dark = brindle(P)
    # седина «соль с перцем» (фото): тёмные темя и кольца вокруг глаз, серые щёки, светлая морда, почти белые брыли
    ax = np.abs(N[:, 0])
    g = np.full(n, 0.22, np.float32) * (1 - 0.50 * np.clip((z - 0.395) / 0.030, 0, 1))
    g = np.maximum(g, 0.62 * np.clip((ax - 0.35) * 2.2, 0, 1) * (z < 0.390))
    muzzle = np.clip((-0.262 - y) / 0.012, 0, 1) * np.clip((0.366 - z) / 0.030, 0, 1)
    g = np.maximum(g, 0.80 * muzzle)
    jowl = np.clip((0.345 - z) / 0.020, 0, 1) * np.clip((-0.240 - y) / 0.02, 0, 1)
    g = np.maximum(g, 1.0 * jowl)
    g = np.maximum(g, 0.62 * np.clip((0.372 - z) / 0.02, 0, 1) * np.clip((-x - 0.025) / 0.02, 0, 1)
                   * (N[:, 1] < 0.2))                                         # правая щека седее (фото)
    for ex, ez in EYES:                                                       # вокруг глаз — тёмное кольцо
        g = g * (1 - 0.75 * np.clip((0.024 - np.hypot(x - ex, z - ez)) / 0.007, 0, 1))
    fleck = vnoise(x * 800, z * 800 + y * 600, 91)
    c = mix(dark, col((0.78, 0.77, 0.75)), np.clip(g + (fleck - 0.5) * 0.55, 0, 1))
    # горло и низ затылка — белые (переходят в белую шею)
    throat = np.clip((0.318 - z) / 0.014, 0, 1) * np.clip((y + 0.250) / 0.02, 0, 1)
    c = mix(c, white_coat(P), throat)
    # проточина (фото спереди): широкая белая полоса на лбу (к темени уходит влево), сужается между глаз
    # и кончается над переносицей; сзади по затылку — узкая
    hw = 0.010 + 0.016 * np.clip((z - 0.356) / 0.070, 0, 1) ** 0.8
    xc = 0.002 + 0.006 * np.clip((z - 0.390) / 0.040, 0, 1)
    hw = np.where(y > -0.215, 0.016 - 0.004 * np.clip((y + 0.215) / 0.025, 0, 1), hw)
    edge = (fbm(x * 260, z * 180 + y * 120, 93) - 0.5) * 0.008
    blaze = np.clip((hw - np.abs(x - xc + edge)) / 0.004, 0, 1) * np.clip((z - 0.355) / 0.006, 0, 1)
    blaze = blaze * (N[:, 1] < 0.45) * np.clip((y + 0.190) / -0.012, 0, 1)
    bw = mix(white_coat(P) * 0.97, col((0.82, 0.79, 0.72)), np.clip((0.366 - z) / 0.010, 0, 1))   # на переносице кремовая
    c = mix(c, bw, blaze)
    # нос: широкая чёрная мочка с ноздрями и бликом
    front = N[:, 1] < -0.25
    roll = np.exp(-((z - 0.366) / 0.004) ** 2) * (np.abs(x) < 0.030) * front     # серый валик над носом
    c = mix(c, col((0.55, 0.54, 0.52)), 0.5 * roll)
    nose = front & (((x / 0.025) ** 2 + ((z - 0.350) / 0.0135) ** 2) < 1.0) & (y < -0.276)
    c = np.where(nose[:, None], col((0.045, 0.042, 0.042)), c)
    for sx in (-1, 1):
        nos = nose & (np.hypot(x - 0.010 * sx, (z - 0.346) * 1.4) < 0.0045)
        c = np.where(nos[:, None], col((0.005, 0.005, 0.005)), c)
    hl = nose & (np.hypot(x + 0.006, z - 0.358) < 0.0030)
    c = np.where(hl[:, None], col((0.15, 0.15, 0.16)), c)
    # розовое пятнышко на морде справа от носа (фото спереди)
    pink = front & (np.hypot(x + 0.021, z - 0.336) < 0.0055) & (y < -0.280)
    c = np.where(pink[:, None], col((0.68, 0.55, 0.53)), c)
    # линия рта: опускается к уголкам под брылями и тает к щекам; бороздка под носом; тёмная нижняя губа
    mz = 0.318 - 0.030 * (x / 0.05) ** 2
    lipz = front & (z < 0.340) & (z > mz - 0.004) & (np.abs(x) < 0.016)       # под носом: тёмные губы (фото)
    c = mix(c, col((0.14, 0.12, 0.12)), lipz.astype(np.float32) * 0.6 * np.clip((0.016 - np.abs(x)) / 0.006, 0, 1))
    lip = front & (z < mz - 0.0012) & (z > mz - 0.0045) & (np.abs(x) < 0.014)
    c = np.where(lip[:, None], col((0.34, 0.25, 0.25)), c)
    mouth = (front & (np.abs(z - mz) < 0.0015)).astype(np.float32)
    c = mix(c, col((0.10, 0.09, 0.09)), mouth * 0.45 * np.clip((0.046 - np.abs(x)) / 0.014, 0, 1))
    phil = front & (np.abs(x) < 0.0020) & (z > 0.323) & (z < 0.336)
    c = mix(c, col((0.12, 0.11, 0.11)), phil.astype(np.float32) * 0.5)
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


def paint_lid(P, N):
    """Закрытый глаз: тёмное тигровое веко, по нижней трети — дуга-щёлка (складка век) с ресницами,
    над ней веко чуть светлее (выпуклость глазного яблока). Края — альфой по эллипсу."""
    x, z = P[:, 0], P[:, 2]
    ex = np.where(x >= 0, EYES[1][0], EYES[0][0]); ez = EYES[0][1]
    dx, dz = (x - ex) / LID_R[0], (z - ez) / LID_R[1]
    e = dx ** 2 + dz ** 2
    alpha = (e < 1.0).astype(np.float32)
    c = mix(brindle(P), col((0.30, 0.28, 0.27)), np.clip(0.35 - 0.35 * e, 0, 0.35))      # выпуклость светлее
    slit = -0.22 - 0.16 * (1 - np.clip(dx, -1, 1) ** 2)                                      # дуга чуть книзу
    line = np.clip(1 - np.abs(dz - slit) / 0.10, 0, 1) * np.clip((0.92 - np.abs(dx)) / 0.15, 0, 1)
    c = mix(c, col((0.015, 0.012, 0.012)), line)
    lash = np.clip(1 - np.abs(dz - slit + 0.13) / 0.06, 0, 1) * np.clip((0.75 - np.abs(dx)) / 0.2, 0, 1)
    c = mix(c, col((0.06, 0.05, 0.05)), 0.5 * lash)
    c = mix(c, col((0.04, 0.035, 0.035)), np.clip((e - 0.70) / 0.30, 0, 1) * 0.6)          # край сливается с ободком
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
    # обратно в чертёжные координаты (в них размечены пятна и морда)
    if tag in ("head", "ear_in", "ear_out", "lid"):
        P = inv_head(P)
    elif tag == "leg_f":
        P = inv_leg(P, "f")
    elif tag == "leg_r":
        P = inv_leg(P, "r")
    elif tag == "paw":
        P = np.where((P[:, 1] < 0)[:, None], inv_leg(P, "f"), inv_leg(P, "r"))
    elif tag != "collar":
        P = inv_body(P)
    u, v = LUV[:, 0], LUV[:, 1]
    ao = 0.55 + 0.45 * _AO if _AO is not None else 1.0
    if tag == "head":
        c = finish(paint_head(P, N), P, N)
    elif tag in ("body", "neck", "leg_r"):
        c = finish(coat(P, N), P, N)
    elif tag == "tail":                                                       # хвостик белый с розовым (фото сзади)
        c = finish(mix(white_coat(P), col((0.74, 0.58, 0.55)), 0.40), P, N)
    elif tag == "leg_f":
        # правая передняя лапа чёрная до запястья (фото спереди и сбоку)
        right = np.clip(-P[:, 0] / 0.02, 0, 1) * np.clip((P[:, 2] - 0.056) / 0.010, 0, 1)   # белый «носок»
        c = finish(coat(P, N, right), P, N)
    elif tag == "paw":
        c = finish(paint_paw(P, N, u, v), P, N, dirt_k=0.8)
    elif tag == "lid":
        c, alpha = paint_lid(P, N)
        c = finish(c, P, N)
    elif tag in ("ear_in", "ear_out"):
        c, alpha = paint_ear(tag, P, N, u, v)
        c = c * np.atleast_1d(ao)[:, None] if _AO is not None else c
    elif tag == "collar":
        c = paint_collar(P, N, u, v)
        c = c * np.atleast_1d(ao)[:, None] if _AO is not None else c
    else:
        c = np.tile(col((0.03, 0.03, 0.03)), (n, 1))
    return np.clip(c, 0, 1), alpha


# =====================================================================================
#  Атлас, скелет, анимации, экспорт
# =====================================================================================
def bake_atlas_ao(mb, me, fsel, aov):
    """Как bake_atlas из build_yurchik_v3.py, но вместе с позицией/нормалью по текселям интерполирует AO вершин."""
    global _AO
    W = H = ATLAS
    Pb = np.zeros((H, W, 3), np.float32); Nb = np.zeros((H, W, 3), np.float32); Lb = np.zeros((H, W, 2), np.float32)
    Ab = np.ones((H, W), np.float32); Tb = np.full((H, W), -1, np.int32)
    tags = sorted(set(mb.ftag)); tid = {t: i for i, t in enumerate(tags)}
    cn = np.empty(len(me.loops) * 3, np.float32); me.corner_normals.foreach_get("vector", cn); cn = cn.reshape(-1, 3)
    for pi, fi in enumerate(fsel):
        ls = me.polygons[pi].loop_start; ids = mb.faces[fi]; t = tid[mb.ftag[fi]]
        px = np.array(mb.fpx[fi], np.float32); pos = np.array([mb.co[i] for i in ids], np.float32)
        nrm = cn[ls:ls + len(ids)]; luv = np.array(mb.fluv[fi], np.float32); av = aov[list(ids)]
        for k in range(1, len(ids) - 1):
            tri = (0, k, k + 1)
            (x0, y0), (x1, y1), (x2, y2) = px[tri[0]], px[tri[1]], px[tri[2]]
            den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(den) < 1e-9:
                continue
            xa = max(int(math.floor(min(x0, x1, x2))) - 1, 0); xb = min(int(math.ceil(max(x0, x1, x2))) + 1, W - 1)
            ya = max(int(math.floor(min(y0, y1, y2))) - 1, 0); yb = min(int(math.ceil(max(y0, y1, y2))) + 1, H - 1)
            X, Yg = np.meshgrid(np.arange(xa, xb + 1) + 0.5, np.arange(ya, yb + 1) + 0.5)
            w0 = ((y1 - y2) * (X - x2) + (x2 - x1) * (Yg - y2)) / den
            w1 = ((y2 - y0) * (X - x2) + (x0 - x2) * (Yg - y2)) / den
            w2 = 1 - w0 - w1
            m = (w0 >= -0.02) & (w1 >= -0.02) & (w2 >= -0.02)
            if not m.any():
                continue
            yy, xx = np.nonzero(m); wa, wb_, wc = w0[m][:, None], w1[m][:, None], w2[m][:, None]
            Pb[ya + yy, xa + xx] = pos[tri[0]] * wa + pos[tri[1]] * wb_ + pos[tri[2]] * wc
            Nb[ya + yy, xa + xx] = nrm[tri[0]] * wa + nrm[tri[1]] * wb_ + nrm[tri[2]] * wc
            Lb[ya + yy, xa + xx] = luv[tri[0]] * wa + luv[tri[1]] * wb_ + luv[tri[2]] * wc
            Ab[ya + yy, xa + xx] = (av[tri[0]] * wa + av[tri[1]] * wb_ + av[tri[2]] * wc)[:, 0]
            Tb[ya + yy, xa + xx] = t
    out = np.zeros((H, W, 4), np.float32)
    for t, i in tid.items():
        m = Tb == i
        if not m.any():
            continue
        Nn = Nb[m]; Nn = Nn / (np.linalg.norm(Nn, axis=1, keepdims=True) + 1e-9)
        _AO = np.clip(Ab[m], 0, 1)
        c, a = paint(t, None, Pb[m], Nn, Lb[m])
        out[m, :3] = c; out[m, 3] = a
    _AO = None
    return Y["fill_invalid4"](out, Tb >= 0, 6), Tb


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


def breath_weights(mb):
    """Бока и брюхо туловища частично переходят с позвонков на Chest/Belly (их дети, в покое совпадают с ними —
    остальные анимации не меняются). Хребет остаётся на позвонках: при вдохе раздуваются только бока."""
    ys = [r[0] * SY for r in T_ST]; zs = [r[1] for r in T_ST]
    body = {i for f, t in enumerate(mb.ftag) if t == "body" for i in mb.faces[f]}
    for vid in body:
        p = mb.co[vid]
        zc = float(np.interp(p.y, ys, zs))
        ang = math.atan2(abs(p.x), p.z - zc)                  # 0 — хребет, π — брюхо
        f = 0.9 * smooth((ang - 0.45) / 1.2)
        w = mb.w[vid]
        for src, dst in (("Spine2", "Chest"), ("Spine1", "Belly")):
            if src in w and f > 0:
                w[dst] = w.get(dst, 0.0) + w[src] * f
                w[src] *= 1 - f


def lids_hide(mb, me, used):
    """Веки (уже раскрашенные на месте) утапливаются в голову: в покое и в дневных анимациях их не видно."""
    remap = {v: k for k, v in enumerate(used)}
    for S_ in "LR":
        ex, ez = EYES[1 if S_ == "L" else 0]
        n = eye_frame(ex, ez)[1] * HEAD_S
        for vid, w in enumerate(mb.w):
            if w.get("Lid" + S_, 0) > 0.5 and vid in remap:
                mb.co[vid] = mb.co[vid] - n * LID_IN
                me.vertices[remap[vid]].co = mb.co[vid]
    me.update()


def lid_open_vec(S_):
    """Сдвиг кости века (в пространстве скелета) — выдвигает веко на глаз."""
    ex, ez = EYES[1 if S_ == "L" else 0]
    return tuple(eye_frame(ex, ez)[1] * HEAD_S * LID_IN)


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
    breath_weights(mb)
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


LOC_BONES = ("Hips", "LidL", "LidR")      # сдвиг ключуется у этих костей (в пространстве скелета)
SCL_BONES = ("Chest", "Belly")            # масштаб (дыхание) — у этих; во всех анимациях, по умолчанию покой


def set_pose(arm, pose):
    pose = dict(pose)
    loc = pose.pop("_loc", {}); scl = pose.pop("_scl", {})
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = qw(arm, pb.name, pose.get(pb.name, []))
    for n in LOC_BONES:
        rq = arm.data.bones[n].matrix_local.to_quaternion()
        arm.pose.bones[n].location = rq.inverted() @ Vector(loc.get(n, (0, 0, 0)))
    for n in SCL_BONES:
        arm.pose.bones[n].scale = scl.get(n, (1, 1, 1))


# ---------- Сон (референс docs/references/hyuga/hyuga_sleep_ref.webp): клубком на боку ----------
# Поза задана для «лежит на левом боку» и зеркалится (SLEEP_DOWN = "R" — на правом, как на фото): тело
# повалено на бок, позвоночник согнут дугой (нос тянется к задним лапам), лапы и морда — внутрь клубка,
# спина — снаружи. Hips задаёт и наклон, и сдвиг: SLEEP_LOC
# подбирается автоматически (fit_sleep) — середина клубка над началом координат, нижняя точка чуть
# утоплена в плед (SLEEP_SINK).
SLEEP_L = 4.5
SLEEP_SINK = 0.006
SLEEP_LOC = (0.0, 0.0, 0.0)


SLEEP_ROLL = 80                                       # насколько повалена на левый бок
SLEEP_CURL = {"Spine1": -70, "Spine2": -70, "Neck": -30, "Head": -55, "Tail": -40}   # изгиб клубка по кости


def sleep_base():
    """Клубок: каждая кость гнётся вокруг ВЕРТИКАЛИ мира (ось, которая после завала на бок смотрит вверх),
    поэтому дуга ложится в плоскость пледа: бок — сгиб в сторону, спина — сгиб вниз в нужной пропорции.
    Подобрано по рендерам (sleep_ref/sleep_top) против референса."""
    c, s = math.cos(math.radians(SLEEP_ROLL)), math.sin(math.radians(SLEEP_ROLL))

    def bend(th):
        return [("z", c * th), ("x", -s * th)]
    p = {
        "Hips": [("y", SLEEP_ROLL)],
        "Spine1": bend(SLEEP_CURL["Spine1"]), "Spine2": bend(SLEEP_CURL["Spine2"]),
        "Neck": [("y", -20)] + bend(SLEEP_CURL["Neck"]) + [("z", 20)],               # шея опускает голову на плед
        "Head": [("y", -25)] + bend(SLEEP_CURL["Head"]) + [("x", 25)],               # морда подогнута к задним лапам
        "Tail": bend(SLEEP_CURL["Tail"]),                                            # хвостик прижат
        "EarL": [("x", -90), ("z", -45)], "EarR": [("x", -60), ("z", -60)],          # уши мягко назад, не торчат
    }
    for S_, add in (("L", 10), ("R", -35)):          # нижние лапы на пледе, верхние свешены на них
        p["Shoulder" + S_] = [("x", 55), ("y", add)]
        p["Forearm" + S_] = [("x", 120)]             # передние подогнуты под грудь
        p["Paw" + S_] = [("x", -20)]
        p["Thigh" + S_] = [("x", -100), ("y", add)]  # задние поджаты к животу
        p["Shin" + S_] = [("x", 110)]
        p["Hock" + S_] = [("x", -80)]
        p["Foot" + S_] = [("x", 30)]
    return mirror_pose(p) if SLEEP_DOWN == "R" else p


SLEEP_DOWN = "R"        # на каком боку лежит: как на референсе — на правом (голова слева, спина от зрителя)
SLEEP_UP = "L" if SLEEP_DOWN == "R" else "R"


def mirror_pose(p):
    """Зеркало позы слева направо: L↔R, повороты вокруг Y и Z меняют знак, сдвиги — по X."""
    sw = lambda n: n[:-1] + {"L": "R", "R": "L"}[n[-1]] if n[-1:] in ("L", "R") and n not in ("Hips",) else n
    out = {}
    for n, v in p.items():
        if n.startswith("_"):
            out[n] = {sw(k): ((-x[0], x[1], x[2]) if n == "_loc" else x) for k, x in v.items()}
        else:
            out[sw(n)] = [(a, -d if a in ("y", "z") else d) for a, d in v]
    return out


def breath_curve(t, L=SLEEP_L):
    """Дыхание спящей собаки: короткий вдох (1.4 с), длинный выдох (2.3 с), пауза до конца цикла. 0…1."""
    t = t % L
    if t < 1.4:
        return smooth(t / 1.4)
    return 1.0 - smooth((t - 1.4) / 2.3)


def pose_sleep(t, L):
    p = sleep_base()
    b = breath_curve(t, L)
    b2 = breath_curve(t - 0.18, L)                                  # живот чуть отстаёт от груди
    p["Spine1"] = p["Spine1"] + [("x", -0.7 * b2)]
    p["Spine2"] = p["Spine2"] + [("x", -0.6 * b)]
    p["Neck"] = p["Neck"] + [("x", 0.5 * b)]
    p["Head"] = p["Head"] + [("x", -0.35 * b)]
    p["_scl"] = {"Chest": (1 + 0.024 * b, 1 + 0.006 * b, 1 + 0.022 * b),
                 "Belly": (1 + 0.020 * b2, 1 + 0.004 * b2, 1 + 0.018 * b2)}
    p["_loc"] = {"Hips": SLEEP_LOC, "LidL": lid_open_vec("L"), "LidR": lid_open_vec("R")}
    return p


# Дрёма — короткие ДОБАВОЧНЫЕ анимации: только отклонение от покоя, без позы сна. В игре они
# накладываются поверх Sleep (AnimationNodeOneShot в режиме ADD, scripts/world/hyuga_sleep.gd), со
# случайной паузой — повтор не читается. Все начинаются и заканчиваются в нуле.
def pose_twitch_ear(t, L):
    """Верхнее ухо дважды вздрагивает, нижнее — чуть-чуть следом."""
    k = math.exp(-((t - 0.35) / 0.07) ** 2) + 0.6 * math.exp(-((t - 0.78) / 0.06) ** 2)
    k2 = 0.35 * math.exp(-((t - 0.95) / 0.08) ** 2)
    p = {"EarR": [("x", 16 * k), ("y", -6 * k)], "EarL": [("x", 10 * k2)]}      # записано для «верхнее — R»
    return mirror_pose(p) if SLEEP_UP == "L" else p


def pose_twitch_paw(t, L):
    """Верхняя передняя лапа «бежит во сне»: три мелких толчка, гаснущих к концу."""
    env = smooth(t / 0.3) * (1 - smooth((t - L + 0.6) / 0.6))
    s = math.sin(2 * math.pi * t * 2.2) * env
    p = {"ForearmR": [("x", -7 * s)], "PawR": [("x", 9 * s)], "ShoulderR": [("x", -3 * s)]}
    return mirror_pose(p) if SLEEP_UP == "L" else p


def pose_sigh(t, L):
    """Вздох: глубокий вдох (1.1 с), задержка, короткий выдох-«пых» и медленный довыдох."""
    s = smooth(t / 1.1) if t < 1.3 else (1 - 0.7 * smooth((t - 1.3) / 0.5)) if t < 1.8 \
        else 0.3 * (1 - smooth((t - 1.8) / (L - 1.8)))
    return {
        "Spine1": [("x", -1.5 * s)], "Spine2": [("x", -1.2 * s)],
        "Neck": [("x", -2.2 * s)], "Head": [("x", 1.2 * s)],
        "_scl": {"Chest": (1 + 0.026 * s, 1 + 0.006 * s, 1 + 0.024 * s),
                 "Belly": (1 + 0.022 * s, 1 + 0.004 * s, 1 + 0.020 * s)},
    }


def fit_sleep(arm, body):
    """Подбирает сдвиг таза для позы сна: середина клубка над началом координат, низ — на SLEEP_SINK в пледе."""
    global SLEEP_LOC
    p = sleep_base()
    p["_loc"] = {"LidL": lid_open_vec("L"), "LidR": lid_open_vec("R")}
    set_pose(arm, p)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    ev.to_mesh_clear()
    mn, mx = co.min(axis=0), co.max(axis=0)
    SLEEP_LOC = (-(mn[0] + mx[0]) / 2, -(mn[1] + mx[1]) / 2, -mn[2] - SLEEP_SINK)
    return {"loc": [round(float(v), 4) for v in SLEEP_LOC], "size": [round(float(v), 3) for v in (mx - mn)]}


def key_pose(arm, pose, f):
    set_pose(arm, pose)
    for pb in arm.pose.bones:
        pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
    for n in LOC_BONES:
        arm.pose.bones[n].keyframe_insert("location", frame=f, group=n)
    for n in SCL_BONES:
        arm.pose.bones[n].keyframe_insert("scale", frame=f, group=n)


def make_anim(arm, name, L, fn, step=2):
    ac = M["new_action"](arm, name)
    N = int(round(L * FPS))
    for f in sorted(set(range(0, N, step)) | {N}):          # последний кадр всегда = первому (шов цикла)
        key_pose(arm, fn(f / FPS if f < N else 0.0, L), f)
    M["push_nla"](arm, ac, name)
    return {"frames": N + 1, "len_s": L}


def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion(); pb.location = (0, 0, 0); pb.scale = (1, 1, 1)


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


SLEEP_VIEWS = [  # поза сна: как на референсе (сверху-сбоку ≈45°, со стороны лап), сверху, сзади по спине
    ("sleep_ref", (-1.0, -1.2, 1.1)), ("sleep_face", (-0.5, 0.866, 1.0)), ("sleep_top", (0.0, 0.0, 1.0)),
    ("sleep_side", (0.5, 0.866, 0.35)),
]


def preview(sc, body, views=PREVIEW_VIEWS, target=(0.0, 0.0, 0.25), prefix="hyuga_"):
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
        cam.location = Vector(target) + d * 3
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y' if abs(d.z) < 0.99 else 'X').to_euler()
        sc.render.filepath = os.path.join(PREVIEW, "%s%s.png" % (prefix, tag))
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
    dens = {"head": 3.0, "body": 1.0, "neck": 1.2, "collar": 0.9, "tail": 0.9}
    for S_ in "LR":
        dens.update({"ear%s_in" % S_: 1.6, "ear%s_out" % S_: 1.1, "f_paw" + S_: 1.4, "r_paw" + S_: 1.3,
                     "lid" + S_: 4.0})
    Y["ISL_DENS"] = dens
    Y["paint"] = paint
    mb = build_all()
    D, pos = Y["pack_islands"](mb, size=ATLAS, pad=3)
    img = bpy.data.images.get(TEX_NAME)
    mats = [Y["make_material"]("HyugaFur", img, False), Y["make_material"]("HyugaEar", img, True)]
    body, fsel, used = Y["make_object"](mb, 0, "HyugaMesh", sc.collection, mats)
    info = {"tris": sum(len(mb.faces[f]) - 2 for f in fsel), "verts": len(used), "atlas": ATLAS,
            "density_px_per_m": round(D, 1)}

    aov = vertex_ao(mb, body.data, fsel, used)
    info["ao_mean"] = round(float(aov[used].mean()), 3)
    rgba, Tb = bake_atlas_ao(mb, body.data, fsel, aov)
    img = save_atlas(rgba)
    for m, a in zip(mats, (False, True)):
        Y["make_material"](m.name, img, a)
    info["atlas_fill"] = round(float((Tb >= 0).mean()), 3)
    lids_hide(mb, body.data, used)

    arm = rig(body, used, mb, sc)
    select_only(sc, [arm], arm)
    bpy.ops.object.mode_set(mode='POSE')
    info["sleep_fit"] = fit_sleep(arm, body)
    info["anims"] = {
        "Idle": make_anim(arm, "Idle", 4.0, pose_idle),
        "Walk": make_anim(arm, "Walk", 0.8, pose_walk, step=1),
        "Sniff": make_anim(arm, "Sniff", 3.0, pose_sniff),
        "LookAround": make_anim(arm, "LookAround", 4.0, pose_look),
        "Sleep": make_anim(arm, "Sleep", SLEEP_L, pose_sleep),
        "SleepTwitchEar": make_anim(arm, "SleepTwitchEar", 1.4, pose_twitch_ear, step=1),
        "SleepTwitchPaw": make_anim(arm, "SleepTwitchPaw", 2.0, pose_twitch_paw, step=1),
        "SleepSigh": make_anim(arm, "SleepSigh", 3.6, pose_sigh),
    }
    reset_pose(arm)
    bpy.ops.object.mode_set(mode='OBJECT')
    export_gltf(sc, arm, body)
    preview(sc, body)
    if PREVIEW:
        select_only(sc, [arm], arm)
        bpy.ops.object.mode_set(mode='POSE')
        set_pose(arm, pose_sleep(0.0, SLEEP_L))
        bpy.ops.object.mode_set(mode='OBJECT')
        preview(sc, body, SLEEP_VIEWS, target=(0.0, 0.0, 0.10))
        reset_pose(arm)
    scene_extras(sc)
    ad = arm.animation_data
    ad.action = bpy.data.actions.get("Idle")
    sc.frame_start, sc.frame_end = 0, int(4.0 * FPS)
    select_only(sc, [arm], arm)
    info["bones"] = len(BONES)
    print("BUILD_HYUGA " + json.dumps(info))
    return info


result = main()
