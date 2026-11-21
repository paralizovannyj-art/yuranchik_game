# -*- coding: utf-8 -*-
# Хьюга (YUR-22), v2: пегий французский бульдог, low-poly модель в стиле PS2 по листу модели
# docs/references/hyuga/hyuga_sheet_v2.webp (виды спереди, слева, справа, сзади и поза отдыха клубком; палитра —
# чёрный, белый, оранжевый ошейник). Старые фото (hyuga_photo_*.png) — дополнительные; где расходятся, прав лист.
# Во сне на диване — как на hyuga_sleep_sofa_v2*.webp.
#
# Устроено так же, как макака (tools/blender/build_monkey.py) и Юрчик (build_yurchik_v3.py) — помощники берутся оттуда:
#   1. Геометрия — «кольца»-сечения, соединённые в трубы. Пропорции сняты с листа (≈1.52 мм на пиксель листа):
#      туловище — 19 колец по 20 точек по гладкой кривой через опорные сечения T_ST (бочка: широкая глубокая грудь
#      ниже локтей, подхват живота, короткая спина, круглый круп; рельеф лопаток, рёбер, паха и крупа); голова —
#      20 горизонтальных колец по 22 точки (столбцы сгущены к морде), в head_pt — короткая широкая морда, мочка носа,
#      валик над носом, стоп, борозда на лбу, надбровья, глаза навыкате, щёки и тяжёлые брыли; шея — толстая труба
#      со складками, ошейник — кольцо поверх неё; лапы — трубы с плечом/бедром, локтем, запястьем, коленом и
#      скакательным суставом плюс компактная лапка с плоской подошвой и четырьмя пальцами; уши-«летучая мышь» —
#      объёмная раковина: вогнутая внутренняя и выпуклая наружная стороны, сшитые ободком толщиной ~4 мм.
#      Голова, уши и веки строятся в «чертёжных» координатах головы и переносятся hx() (крупнее и ниже к груди).
#   2. Развёртка — прямоугольные островки, упакованные в один атлас 1024×1024 (морде нужна плотность).
#   3. Текстура — процедурная: белая шерсть с крапом, чёрные пятна — 3D-эллипсоиды по видам листа (плечо до
#      локтя, рёбра, седло поперёк спины, круп с задней стороной бёдер), чёрная голова с белой проточиной, седая
#      морда, глаза с белком в уголке, нос, складки, розоватая кожа на брюхе и в ушах, ошейник с пряжкой.
#      В текстуру запечены мягкий свет и затенение (AO: лучи из каждой вершины по полусфере) — отсюда объём.
#   Сравнение с листом в тех же ракурсах и масштабе — tools/blender/hyuga_compare.py.
#   4. Скелет — свой: таз, 2 позвонка, шея, голова, уши, хвост; передние лапы по 3 кости, задние по 4. Поза покоя — стоит.
#      Листовые кости: Chest/Belly (масштаб раздувает бока при дыхании), LidL/LidR (закрытые веки — в покое
#      утоплены в голову, во сне выдвигаются на глаза).
#   5. Анимации — процедурные ключи: Idle (4 с), Walk (рысь на месте, 0.8 с), Sniff (нюхает землю, 3 с),
#      LookAround (4 с), Sleep (спит клубком на боку и дышит, 4.5 с, как «Resting pose» листа; поза ставится
#      по точкам контакта с пледом — см. «Сон» ниже). Все зациклены.
#      Добавочные (только отклонение от покоя, для наложения поверх Sleep): SleepTwitchEar, SleepTwitchPaw, SleepSigh.
#      В игре: scripts/world/hyuga_sleep.gd (диван в scenes/levels/stairwell.tscn).
#
# Масштаб (замер готовой модели): холка ≈ 0.30 м, макушка ≈ 0.39 м, кончики ушей ≈ 0.435 м, длина от носа до
# крупа ≈ 0.50 м, ширина ≈ 0.21 м — пропорции листа v2 при холке 0.30 м (Юрчик — 1.783 м: собака ему ниже колена).
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
ATLAS = 1024
DENS_K = 2.0
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
#  Геометрия (v2, по листу docs/references/hyuga/hyuga_sheet_v2.webp). Всё — сразу в итоговых координатах.
#  Масштаб листа: ≈1.52 мм на пиксель (холка 0.30 м). Замеры — в комментариях у таблиц.
# =====================================================================================
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


def wfn(names, power=4.0, design=False):
    """Веса «по расстоянию до кости»: обратная степень расстояния, две ближайшие кости.
    design=True — для частей головы, которые строятся в «чертёжных» координатах головы (до hx)."""
    def f(p):
        p = Vector(p)
        bones = BONE_D if design else BONE
        ds = sorted((max(seg_dist(p, *bones[n]), 1e-4), n) for n in names)[:2]
        w = {n: d ** -power for d, n in ds}
        tot = sum(w.values())
        return {n: x / tot for n, x in w.items() if x / tot > 0.02}
    return f


# ---------- Туловище ----------
# Опорные сечения: (y, верх, низ, полуширина, высота самого широкого места). Бочка: грудь широкая и глубокая,
# опущена ниже локтей (z≈0.112), подхват живота к паху (z≈0.17), короткая спина, круп чуть выше холки и круглый.
T_ST = [
    (-0.182, 0.262, 0.172, 0.050, 0.212),
    (-0.168, 0.278, 0.140, 0.072, 0.200),
    (-0.145, 0.290, 0.120, 0.086, 0.190),
    (-0.112, 0.298, 0.110, 0.093, 0.186),
    (-0.075, 0.301, 0.108, 0.097, 0.190),
    (-0.035, 0.300, 0.116, 0.099, 0.198),
    (0.005, 0.298, 0.134, 0.095, 0.208),
    (0.042, 0.299, 0.152, 0.087, 0.218),
    (0.076, 0.302, 0.166, 0.081, 0.226),
    (0.106, 0.304, 0.174, 0.082, 0.230),
    (0.134, 0.300, 0.176, 0.086, 0.232),
    (0.158, 0.289, 0.174, 0.083, 0.232),
    (0.176, 0.272, 0.178, 0.070, 0.230),
    (0.189, 0.252, 0.188, 0.046, 0.226),
]
T_FRONT, T_REAR = (0, -0.191, 0.218), (0, 0.196, 0.224)
T_STATIONS = 19
T_COLS = 20


def torso_ring(y, zt, zb, a, zw):
    pts = []
    for k in range(T_COLS):
        th = 2 * math.pi * k / T_COLS                          # 0 — хребет, 90° — левый бок (+X), 180° — брюхо
        s, c = math.sin(th), math.cos(th)
        if c >= 0:                                             # верх: широкая плоская спина
            x = a * sgnpow(s, 2 / 2.7); z = zw + (zt - zw) * sgnpow(c, 2 / 2.5)
        else:                                                  # низ: рёбра к килю груди сужаются
            keel = 1.0 - 0.22 * (-c) ** 1.5
            x = a * sgnpow(s, 2 / 2.3) * keel; z = zw + (zw - zb) * sgnpow(c, 2 / 2.2)
        at = abs(math.atan2(s, c))                             # 0 — хребет, π — брюхо
        bump = (0.007 * gauss(y, -0.085, 0.030) * gauss(at, 0.62, 0.28)        # лопатки
                - 0.003 * gauss(at, 0.0, 0.22) * gauss(y, 0.02, 0.09)            # ложбинка хребта
                + 0.004 * gauss(y, -0.030, 0.05) * gauss(at, 1.75, 0.45)          # рёбра
                - 0.007 * gauss(y, 0.085, 0.030) * gauss(at, 1.95, 0.40)          # пах: подхват перед бедром
                + 0.005 * gauss(y, 0.150, 0.030) * gauss(at, 0.85, 0.35))         # мышцы крупа
        L = math.hypot(x, z - zw) or 1.0
        pts.append((x + x / L * bump, y, z + (z - zw) / L * bump))
    return pts


def build_torso(mb):
    w = wfn(["Hips", "Spine1", "Spine2"])
    rings = [[mb.vert(T_FRONT, w(T_FRONT))] * T_COLS]
    for st in catmull(T_ST, T_STATIONS):
        pts = torso_ring(*st)
        rings.append(mb.ring(pts, [w(p) for p in pts]))
    rear = mb.vert(T_REAR, w(T_REAR))
    loft(mb, rings, "body", "body", seam=T_COLS // 2, pole=rear)


# ---------- Голова ----------
# Голова, уши и веки строятся в своих «чертёжных» координатах (таблицы ниже), потом hx() увеличивает голову
# и опускает её к груди на короткую шею. Раскраска головы считается обратно в чертёжных (hx_inv).
HEAD_P = Vector((0, -0.196, 0.334))
HEAD_S = 1.12
HEAD_T = Vector((0, 0.006, -0.030))


def hx(p):
    return HEAD_P + (Vector(p) - HEAD_P) * HEAD_S + HEAD_T


def hx_inv(P):
    pv, t = np.array(HEAD_P, np.float32), np.array(HEAD_T, np.float32)
    return (P - pv - t) / HEAD_S + pv


# Горизонтальные сечения: (z, полуширина, затылок y, плоскость лица y). Квадратная массивная голова с плоским
# широким лбом; морда, валик над носом, стоп, надбровья, брыли, щёки и глаза навыкате — «бугры» в head_pt.
H_CTRL = np.array([
    (0.278, 0.044, -0.205, -0.246), (0.290, 0.056, -0.188, -0.254), (0.302, 0.061, -0.178, -0.258),
    (0.318, 0.065, -0.170, -0.261), (0.334, 0.066, -0.166, -0.263), (0.350, 0.066, -0.164, -0.263),
    (0.365, 0.064, -0.165, -0.261), (0.380, 0.061, -0.168, -0.256), (0.392, 0.056, -0.174, -0.248),
    (0.400, 0.048, -0.182, -0.238), (0.405, 0.036, -0.192, -0.226), (0.408, 0.020, -0.200, -0.214),
])
H_ZS = [0.279, 0.285, 0.292, 0.299, 0.307, 0.315, 0.323, 0.331, 0.338, 0.344, 0.350, 0.357, 0.364, 0.372,
        0.380, 0.388, 0.395, 0.400, 0.404, 0.407]
H_COLS = 22
EYES = [(-0.036, 0.355), (0.036, 0.355)]          # центры глаз (x, z): широко, по бокам от стопа
EYE_R = 0.0112
NOSE = (0.0, 0.336)                               # центр мочки носа (x, z)


def h_th(k):
    """Угол столбца головы: столбцы сгущены к морде (там мелкие детали), реже — к затылку."""
    s = 2 * math.pi * k / H_COLS
    return s - 0.32 * math.sin(s)


def head_pt(z, th):
    """Точка головы на высоте z, угол th (0 — лицо, 90° — левая щека)."""
    a = float(np.interp(z, H_CTRL[:, 0], H_CTRL[:, 1]))
    yb = float(np.interp(z, H_CTRL[:, 0], H_CTRL[:, 2])); yf = float(np.interp(z, H_CTRL[:, 0], H_CTRL[:, 3]))
    yc, d = (yb + yf) / 2, (yb - yf) / 2
    c = math.cos(th)
    x, y = sellipse(a, d, d, yc, th, 2.8 if c > 0 else 2.1)
    at = abs(math.atan2(math.sin(th), c))                      # 0 — лицо, π — затылок
    sx = 1.0 if x >= 0 else -1.0
    ax = abs(x)
    fr = max(0.0, c) ** 0.5                                    # только лицевая сторона
    # морда: короткий широкий «кирпичик» (нос на 3 см впереди стопа)
    mz = smooth((z - 0.282) / 0.018) * (1 - smooth((z - 0.340) / 0.014))
    y -= 0.021 * mz * math.exp(-(ax / 0.050) ** 3) * fr
    # нижняя челюсть: подбородок чуть выступает (у бульдога прикус «вперёд»)
    y -= 0.014 * gauss(z, 0.284, 0.007) * math.exp(-(ax / 0.026) ** 2) * fr
    # мочка носа: широкая плоская, чуть выступает
    y -= 0.004 * math.exp(-((x - NOSE[0]) / 0.017) ** 4 - ((z - NOSE[1]) / 0.010) ** 4) * fr
    # валик-складка поперёк над носом, под ней — бороздка
    y -= 0.006 * gauss(z, 0.350, 0.0042) * math.exp(-(ax / 0.034) ** 4) * fr
    # стоп: глубокая впадина между глазами + вертикальная борозда на лбу
    y += 0.009 * gauss(z, 0.358, 0.006) * math.exp(-(ax / 0.020) ** 2) * fr
    y += 0.004 * smooth((z - 0.359) / 0.010) * (1 - smooth((z - 0.392) / 0.010)) * math.exp(-(ax / 0.007) ** 2) * fr
    # надбровья
    y -= 0.004 * gauss(z, 0.372, 0.007) * gauss(ax, 0.034, 0.013) * fr
    # глаза навыкате
    for ex, ez in EYES:
        y -= 0.0045 * math.exp(-((x - ex) ** 2 + (z - ez) ** 2) / 0.0105 ** 2) * fr
    # щёки и скулы
    x += sx * 0.006 * gauss(z, 0.328, 0.020) * gauss(at, 1.25, 0.45)
    # брыли: тяжело свисают ниже нижней челюсти по бокам морды
    jw = gauss(at, 0.80, 0.34)
    x += sx * 0.012 * jw * (1 - smooth((z - 0.295) / 0.032))
    zz = z - 0.018 * jw * math.exp(-((z - 0.279) / 0.011) ** 2)
    return (x, y, zz)


def build_head(mb):
    w = {"Head": 1.0}
    rings = [[mb.vert((0, -0.214, 0.281), w)] * H_COLS]
    for z in H_ZS:
        rings.append(mb.ring([head_pt(z, h_th(k)) for k in range(H_COLS)], w))
    top = mb.vert((0, -0.206, 0.4085), w)
    loft(mb, rings, "head", "head", seam=H_COLS // 2, pole=top)


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
    """Центр глаза на поверхности головы и наружная нормаль."""
    th = head_th(ez, ex)
    c = Vector(head_pt(ez, th))
    du = Vector(head_pt(ez, th + 0.02)) - Vector(head_pt(ez, th - 0.02))
    dv = Vector(head_pt(ez + 0.002, th)) - Vector(head_pt(ez - 0.002, th))
    n = du.cross(dv).normalized()
    if n.y > 0:
        n = -n
    return c, n


# ---------- Уши ----------
# Большие стоячие «летучая мышь»: широкое основание, круглый верх, раскрыты вперёд и чуть наружу.
# Объёмная раковина: внутренняя (вогнутая) и наружная (выпуклая) стороны сшиты по краю ободком толщиной ~4 мм.
EAR_BASE = Vector((0.041, -0.194, 0.380))
EAR_H, EAR_W = 0.092, 0.060


def ear_frame(sx):
    up = Vector((0.36 * sx, 0.10, 1.0)).normalized()
    nrm = Vector((0.32 * sx, -1.0, 0.0)); nrm = (nrm - up * nrm.dot(up)).normalized()   # куда раскрыта раковина
    side = nrm.cross(up)
    if side.x * sx < 0:
        side = -side
    return Vector((EAR_BASE.x * sx, EAR_BASE.y, EAR_BASE.z)), up, nrm, side


EAR_NI, EAR_NV = 7, 9


def ear_hw(v):
    if v < 0.40:
        return EAR_W / 2 * (1 - 0.12 * v)
    return EAR_W / 2 * 0.952 * max(0.0, 1 - ((v - 0.40) / 0.62) ** 1.6) ** 0.6


def build_ear(mb, sx):
    S_ = "L" if sx > 0 else "R"
    base, up, nrm, side = ear_frame(sx)
    w = wfn(["Head", "Ear" + S_], design=True)
    rows = []
    for j in range(EAR_NV):
        v = j / EAR_NV
        hw = ear_hw(v)
        row = []
        for front in (True, False):
            for i in (range(EAR_NI) if front else range(EAR_NI - 1, -1, -1)):
                u = i / (EAR_NI - 1) * 2 - 1
                cup = 0.012 * (1 - u * u) * math.sin(math.pi * min(v * 1.15 + 0.08, 1.0))   # глубина раковины
                roll = 0.004 * u * u * min(v * 1.6, 1.0)                                       # края завёрнуты вперёд
                thick = 0.0038 + 0.0022 * (1 - u * u) * (1 - v)                                # толще к середине и низу
                off = -cup + roll - (0.0 if front else thick)
                k = 1.0 if front else 1.04                                                      # тыльная чуть шире
                row.append(base + side * (u * hw * k) + up * (v * EAR_H - 0.016) + nrm * off)
        rows.append(mb.ring(row, [w(p) for p in row]))
    tip = base + up * (EAR_H - 0.016) + nrm * (-0.002)
    pole = mb.vert(tip, w(tip))
    inner = lambda i, j0, j1: "ear_in" if j0 < EAR_NI and j1 < EAR_NI else "ear_out"
    loft(mb, rows, "ear" + S_, "ear_out", seam=EAR_NI + EAR_NI // 2, pole=pole, tagfn=inner,
         inside=base + up * 0.03 - nrm * 0.01)


# ---------- Шея и ошейник ----------
NECK = [Vector((0, -0.098, 0.236)), hx((0, -0.207, 0.350))]
NECK_R = [(0.0, 0.088, 0.084), (0.45, 0.077, 0.073), (1.0, 0.058, 0.056)]   # (t, бок, вперёд-назад): толстая
NECK_SIDES = 14


def neck_at(t):
    p = NECK[0].lerp(NECK[1], t)
    ts = [r[0] for r in NECK_R]
    return p, (float(np.interp(t, ts, [r[1] for r in NECK_R])), float(np.interp(t, ts, [r[2] for r in NECK_R])))


def neck_w(p):
    """Веса шеи и ошейника — по положению вдоль оси шеи: кольцо гнётся целиком, ошейник не встаёт гребнем."""
    d = NECK[1] - NECK[0]
    t = max(0.0, min(1.0, (Vector(p) - NECK[0]).dot(d) / d.length_squared))
    if t < 0.5:
        k = smooth(t / 0.5)
        return {n: x for n, x in (("Spine2", 1 - k), ("Neck", k)) if x > 0.02}
    k = smooth((t - 0.5) / 0.5)
    return {n: x for n, x in (("Neck", 1 - k), ("Head", k)) if x > 0.02}


NECK_TS = [0.0, 0.16, 0.30, 0.38, 0.47, 0.58, 0.72, 0.86, 1.0]
NECK_FOLD = {0.30: 1.025, 0.58: 1.015}        # складки кожи под ошейником и над ним


def build_neck(mb):
    path, radii = [], []
    for t in NECK_TS:
        p, (rs, ru) = neck_at(t)
        k = NECK_FOLD.get(t, 1.0)
        path.append(p); radii.append((rs * k, ru * k))
    tube(mb, path, radii, NECK_SIDES, "neck", "neck", neck_w, cap_end=0, cap_start=0.3, ref=(0, -1, 0))


COLLAR_T = (0.43, 0.455, 0.505, 0.53)


def build_collar(mb):
    """Оранжевый ошейник: кольцо шире шеи (шея прямая — рамка трубы та же, вершины ошейника над вершинами шеи)."""
    path, radii = [], []
    for t, grow in zip(COLLAR_T, (0.003, 0.0065, 0.0065, 0.003)):
        p, (rs, ru) = neck_at(t)
        path.append(p); radii.append((rs + grow, ru + grow))
    tube(mb, path, radii, NECK_SIDES, "collar", "collar", neck_w, cap_end=0, ref=(0, -1, 0))


# ---------- Веки ----------
LID_R = (0.0150, 0.0135)     # полуоси века (поперёк, вверх)
LID_IN = 0.014               # насколько веко утоплено в голову в покое (по нормали глаза)


def build_lid(mb, sx):
    """Закрытое веко: выпуклая пластинка поверх глаза. Строится на месте (запекаются цвет и AO), потом (lids_hide)
    утапливается в голову; в позе сна кость LidL/LidR выдвигает его обратно."""
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
            row.append(p + n * (0.0012 + 0.0024 * dome))
        rows.append(mb.ring(row, w))
    loft(mb, rows, "lid" + S_, "lid", closed=False, mat=1, direction=n)


# ---------- Лапы ----------
# Передняя: лопатка (внутри корпуса) → плечо → мощное плечо-предплечье → чёткий локоть сзади → прямое
# предплечье → узкое запястье → пясть. Задняя: таз → толстое бедро → колено → голень → скакательный сустав.
# (точка, (бок, вперёд-назад)) — замер по видам сбоку и спереди.
FRONT_LEG = [((0.052, -0.080, 0.258), (0.030, 0.044)), ((0.066, -0.110, 0.218), (0.033, 0.047)),
             ((0.074, -0.114, 0.180), (0.033, 0.045)), ((0.077, -0.104, 0.146), (0.030, 0.041)),
             ((0.077, -0.096, 0.122), (0.025, 0.033)), ((0.075, -0.098, 0.094), (0.021, 0.024)),
             ((0.073, -0.100, 0.064), (0.019, 0.020)), ((0.072, -0.101, 0.042), (0.016, 0.017)),
             ((0.072, -0.104, 0.022), (0.018, 0.019))]
REAR_LEG = [((0.048, 0.122, 0.268), (0.036, 0.056)), ((0.060, 0.128, 0.232), (0.040, 0.060)),
            ((0.068, 0.130, 0.192), (0.040, 0.056)), ((0.072, 0.118, 0.156), (0.034, 0.046)),
            ((0.073, 0.108, 0.132), (0.028, 0.036)), ((0.073, 0.124, 0.106), (0.024, 0.032)),
            ((0.073, 0.148, 0.082), (0.020, 0.026)), ((0.073, 0.162, 0.062), (0.017, 0.021)),
            ((0.073, 0.163, 0.042), (0.015, 0.017)), ((0.073, 0.160, 0.022), (0.017, 0.018))]
LEG_SIDES = 10


def flat_sole(mb, a, z0=0.002):
    """Подошва лапы — плоская (вершины ниже z0 прижимаются к полу)."""
    for i in range(a, len(mb.co)):
        if mb.co[i].z < z0:
            mb.co[i] = Vector((mb.co[i].x, mb.co[i].y, z0))


def build_paw(mb, xc, y0, y1, isl, w):
    """Компактная лапка: кольца от пятки к пальцам, плоская подошва, спереди 4 пальца-«бугорка»."""
    NC = 12
    prof = [(0.00, 0.014, 0.020), (0.20, 0.019, 0.028), (0.42, 0.021, 0.027), (0.62, 0.022, 0.022),
            (0.80, 0.021, 0.016), (0.93, 0.018, 0.010)]
    a = len(mb.co)
    rings = []
    heel = Vector((xc, y0 - 0.003 * (1 if y1 > y0 else -1), 0.012))
    rings.append([mb.vert(heel, w(heel))] * NC)
    for t, hw, h in prof:
        y = y0 + (y1 - y0) * t
        pts = []
        for k in range(NC):
            th = 2 * math.pi * k / NC
            s, c = math.sin(th), math.cos(th)
            xn = sgnpow(s, 0.75)
            x = xc + hw * xn
            z = h * 0.5 * (1 + sgnpow(c, 0.7))
            yy = y
            if t > 0.55 and z > 0.003:                          # пальцы: волна вдоль переднего края
                toe = abs(math.sin(2 * math.pi * xn))
                yy += (y1 - y0) * 0.10 * (toe - 0.5) * (t - 0.55) / 0.38
                z -= 0.0025 * (1 - toe) * max(c, 0)
            pts.append((x, yy, z))
        rings.append(mb.ring(pts, [w(p) for p in pts]))
    tip = Vector((xc, y1, 0.005))
    pole = mb.vert(tip, w(tip))
    fis = loft(mb, rings, isl, "paw", seam=NC // 2, pole=pole)
    M["orient_tube"](mb, fis, [heel, Vector((xc, y0 + (y1 - y0) * 0.5, 0.012)), tip])
    flat_sole(mb, a)


def build_front_leg(mb, sx):
    S_ = "L" if sx > 0 else "R"
    m = lambda p: (p[0] * sx, p[1], p[2])
    tube(mb, [m(p) for p, r in FRONT_LEG], [r for p, r in FRONT_LEG], LEG_SIDES, "f_leg" + S_, "leg_f",
         wfn(["Spine2", "Shoulder" + S_, "Forearm" + S_, "Paw" + S_]), cap_end=0, ref=(0, -1, 0))
    build_paw(mb, 0.072 * sx, -0.080, -0.140, "f_paw" + S_, wfn(["Forearm" + S_, "Paw" + S_]))


def build_rear_leg(mb, sx):
    S_ = "L" if sx > 0 else "R"
    m = lambda p: (p[0] * sx, p[1], p[2])
    tube(mb, [m(p) for p, r in REAR_LEG], [r for p, r in REAR_LEG], LEG_SIDES, "r_leg" + S_, "leg_r",
         wfn(["Hips", "Thigh" + S_, "Shin" + S_, "Hock" + S_, "Foot" + S_]), cap_end=0, ref=(0, -1, 0))
    build_paw(mb, 0.073 * sx, 0.178, 0.120, "r_paw" + S_, wfn(["Hock" + S_, "Foot" + S_]))


def build_tail(mb):
    """Короткий загнутый обрубок, прижат к крупу."""
    tube(mb, [(0, 0.180, 0.256), (0.002, 0.192, 0.254), (0.004, 0.196, 0.247), (0.002, 0.195, 0.241)],
         [0.012, 0.011, 0.008, 0.005], 8, "tail", "tail", wfn(["Hips", "Tail"]), cap_end=0.8)


def build_all():
    mb = MB()
    build_torso(mb)
    build_neck(mb); build_collar(mb)
    a = len(mb.co)
    build_head(mb)
    for sx in (1, -1):
        build_ear(mb, sx); build_lid(mb, sx)
    for i in range(a, len(mb.co)):                          # голова, уши, веки: чертёжные → итоговые
        mb.co[i] = hx(mb.co[i])
    for sx in (1, -1):
        build_front_leg(mb, sx); build_rear_leg(mb, sx)
    build_tail(mb)
    return mb


# =====================================================================================
#  Скелет: (имя, голова, хвост, родитель). Правая сторона — зеркало левой.
# =====================================================================================
def _lid_bone():
    c, n = eye_frame(*EYES[1])
    return tuple(c), tuple(c + n * 0.028)


def _ear_bone():
    base, up, nrm, side = ear_frame(1)
    return tuple(base), tuple(base + up * 0.07)


LEFT_BONES = [
    ("Shoulder", (0.068, -0.116, 0.208), (0.077, -0.097, 0.124), "Spine2"),
    ("Forearm", (0.077, -0.097, 0.124), (0.072, -0.101, 0.030), "Shoulder"),
    ("Paw", (0.072, -0.101, 0.030), (0.072, -0.134, 0.010), "Forearm"),
    ("Thigh", (0.060, 0.128, 0.232), (0.073, 0.108, 0.132), "Hips"),
    ("Shin", (0.073, 0.108, 0.132), (0.073, 0.162, 0.062), "Thigh"),
    ("Hock", (0.073, 0.162, 0.062), (0.073, 0.162, 0.022), "Shin"),
    ("Foot", (0.073, 0.162, 0.022), (0.073, 0.128, 0.010), "Hock"),
    ("Ear",) + _ear_bone() + ("Head",),
    ("Lid",) + _lid_bone() + ("Head",),           # веко: в покое спрятано в голове
]
BONES = [
    ("Hips", (0, 0.135, 0.252), (0, 0.035, 0.256), None),
    ("Spine1", (0, 0.035, 0.256), (0, -0.065, 0.262), "Hips"),
    ("Spine2", (0, -0.065, 0.262), (0, -0.120, 0.266), "Spine1"),
    ("Neck", (0, -0.118, 0.262), tuple(HEAD_P), "Spine2"),
    ("Head", (0, -0.196, 0.334), (0, -0.212, 0.420), "Neck"),
    ("Tail", (0, 0.186, 0.258), (0, 0.207, 0.238), "Hips"),
    # дыхание: листовые кости в середине груди и живота — их масштаб раздувает бока и брюхо (хребет не трогают)
    ("Chest", (0, -0.075, 0.200), (0, -0.125, 0.200), "Spine2"),
    ("Belly", (0, 0.050, 0.218), (0, 0.000, 0.218), "Spine1"),
]
for _n, _h, _t, _p in LEFT_BONES:
    for _sx, _suf in ((1, "L"), (-1, "R")):
        BONES.append((_n + _suf, (_h[0] * _sx, _h[1], _h[2]), (_t[0] * _sx, _t[1], _t[2]),
                      _p if _p in ("Spine2", "Hips", "Head") else _p + _suf))
BONE_D = {n: (Vector(h), Vector(t)) for n, h, t, p in BONES}      # голова/уши/веки — в чертёжных координатах


def _final(n, h, t):
    if n == "Head" or n[:3] in ("Ear", "Lid"):
        return hx(h), hx(t)
    if n == "Neck":
        return Vector(h), hx(t)
    return Vector(h), Vector(t)


BONE = {n: _final(n, h, t) for n, h, t, p in BONES}
BONE_F = BONE


# =====================================================================================
#  Запечённое затенение (AO): лучи из каждой вершины по полусфере, препятствия — сама собака и пол
# =====================================================================================
def vertex_ao(mb, me, fsel, used, rays=64, maxd=0.10):
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
        aov[vid] = max(0.2, 1.0 - occ / rays)
    return aov


# =====================================================================================
#  Раскраска (процедурная, по листу v2)
# =====================================================================================
WHITE = (0.90, 0.895, 0.87)
BLACK = (0.070, 0.067, 0.070)
# чёрные пятна: (центр (|x|, y, z), полуоси, сдвиг центра на правом боку) — эллипсоиды в метрах.
# Виды сбоку: пятно на плече и плечевой кости до локтя, большое пятно на рёбрах/спине, седло поперёк спины,
# круп с заходом на заднюю сторону бёдер. Вид сзади: белая полоса под хвостом, белые «штаны» между бёдрами.
PATCHES = [
    ((0.086, -0.100, 0.182), (0.040, 0.030, 0.056), (0.000, 0.004, 0.000)),    # передняя доля — плечо до локтя
    ((0.080, -0.040, 0.232), (0.060, 0.045, 0.070), (0.000, -0.004, 0.006)),   # пятно на рёбрах за лопаткой
    ((0.000, 0.036, 0.296), (0.118, 0.046, 0.046), (0.000, 0.006, 0.000)),     # седло поперёк спины
    ((0.000, 0.150, 0.258), (0.150, 0.056, 0.090), (0.000, 0.000, 0.000)),     # круп
    ((0.072, 0.176, 0.196), (0.055, 0.030, 0.050), (0.000, -0.004, 0.006)),    # задняя сторона бёдер
]
_AO = None          # затенение по текселям (bake_atlas_ao кладёт сюда массив перед раскраской каждого тега)
KEY = np.array((0.30, -0.42, 0.86), np.float32); KEY /= np.linalg.norm(KEY)   # запечённый «ключевой» свет


def black_mask(P):
    ax = np.abs(P[:, 0]); right = (P[:, 0] < 0).astype(np.float32)[:, None]
    m = np.zeros(len(P), np.float32)
    for k, (c, r, dr) in enumerate(PATCHES):
        cc = np.array(c, np.float32)[None, :] + right * np.array(dr, np.float32)[None, :]
        Q = np.stack([ax, P[:, 1], P[:, 2]], axis=1)
        d = (((Q - cc) / np.array(r, np.float32)) ** 2).sum(axis=1)
        n = fbm(Q[:, 0] * 55 + Q[:, 1] * 40 + k * 3.1, Q[:, 2] * 55 + Q[:, 1] * 25 + P[:, 0] * 9, 61 + k) - 0.5
        hair = vnoise(Q[:, 0] * 700 + Q[:, 1] * 500, Q[:, 2] * 700, 67 + k) - 0.5      # рваный край из шерстинок
        m = np.maximum(m, np.clip((1.0 - d + 0.55 * n + 0.10 * hair) * 9.0, 0, 1))
    under_tail = np.clip((0.024 - ax) / 0.010, 0, 1) * np.clip((0.246 - P[:, 2]) / 0.012, 0, 1) \
        * np.clip((P[:, 1] - 0.165) / 0.010, 0, 1)
    return m * (1 - under_tail)


def _hash(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = h & 0xFFFFFFFF
    out = []
    for _ in range(5):
        h = (h * 1103515245 + 12345) & 0x7FFFFFFF
        out.append((h >> 8).astype(np.float32) / float(1 << 23))
    return out


def ticks(P, cell, prob, rmin, rmax, seed):
    """Крап: мелкие чёрные пятнышки (случайные точки в ячейках сетки), край чуть размыт."""
    g = np.floor(P / cell).astype(np.int64)
    out = np.zeros(len(P), np.float32)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                ix, iy, iz = g[:, 0] + dx, g[:, 1] + dy, g[:, 2] + dz
                r = _hash(ix, iy, iz, seed)
                ctr = np.stack([ix + r[0], iy + r[1], iz + r[2]], axis=1) * cell
                rad = rmin + (rmax - rmin) * r[3] ** 2
                d = np.linalg.norm((P - ctr) * np.array((1.0, 0.8, 1.25)), axis=1)
                on = (r[4] < prob).astype(np.float32)
                out = np.maximum(out, on * np.clip((rad - d) / (0.45 * rad), 0, 1))
    return out


def black_coat(P, N):
    """Чёрная гладкая шерсть: почти чёрная, с лёгким холодным блеском на верхних гранях."""
    s = fbm(P[:, 0] * 150 + P[:, 1] * 110, P[:, 2] * 150, 71)
    c = np.tile(col(BLACK), (len(P), 1)) * (0.85 + 0.35 * s)[:, None]
    sheen = np.clip(N[:, 2] * 0.6 + 0.2 - N[:, 1] * 0.2, 0, 1) ** 2
    return c + col((0.10, 0.105, 0.115)) * sheen[:, None]


def white_coat(P):
    s = fbm(P[:, 0] * 160 + P[:, 1] * 120, P[:, 2] * 90 + P[:, 1] * 40, 81)
    return col(WHITE) * (0.95 + 0.07 * s)[:, None]


def fur(c, P):
    """Лёгкий шум короткой шерсти: тонкие пряди вдоль тела (по Y) + мелкое зерно."""
    strand = vnoise(P[:, 0] * 900 + P[:, 2] * 700, P[:, 1] * 160, 9)
    grain = vnoise(P[:, 0] * 1500 + P[:, 1] * 900, P[:, 2] * 1500, 11)
    return c * (0.95 + 0.07 * (strand - 0.5) + 0.05 * (grain - 0.5))[:, None]


def finish(c, P, N, dirt_k=1.0):
    """Шерсть, лёгкая грязь со снега на лапах, запечённый свет и AO."""
    c = fur(c, P)
    low = np.clip((0.05 - P[:, 2]) / 0.045, 0, 1)
    dirt = (0.3 + 0.7 * fbm(P[:, 0] * 120 + 3, P[:, 1] * 120 + P[:, 2] * 60, 17)) * low * 0.30 * dirt_k
    c = mix(c, c * col((0.70, 0.66, 0.62)), np.clip(dirt, 0, 0.3))
    return c * shade(P, N)[:, None]


def shade(P, N):
    """Объём: мягкий свет сверху-спереди-слева + запечённое затенение (AO) по складкам, под брюхом и у пола."""
    ndl = np.clip(N @ KEY * 0.5 + 0.5, 0, 1)
    light = 0.72 + 0.34 * ndl ** 1.3
    sky = 0.96 + 0.05 * N[:, 2]
    ao = 0.40 + 0.60 * _AO ** 1.3 if _AO is not None else 0.74 + 0.26 * np.clip(P[:, 2] / 0.05, 0, 1)
    belly = 1.0 - 0.12 * np.clip(-N[:, 2] - 0.4, 0, 1)
    return light * sky * ao * belly


def coat(P, N, tick_prob=0.40):
    m = black_mask(P)
    c = mix(white_coat(P), black_coat(P, N), m)
    # крап на белом: гуще на лапах, редкий на боках, почти нет на груди и шее
    low = np.clip((0.20 - P[:, 2]) / 0.10, 0, 1)
    side = np.clip((np.abs(N[:, 0]) - 0.3) / 0.4, 0, 1)
    prob = tick_prob * (0.35 + 0.65 * np.maximum(low, side * 0.8))
    t = ticks(P, 0.012, 1.0, 0.0016, 0.0046, 5) * (vnoise(P[:, 0] * 80, P[:, 1] * 80 + P[:, 2] * 60, 7) < prob)
    c = mix(c, black_coat(P, N) * 1.4, t * (1 - m) * 0.9)
    # розоватая кожа на брюхе (шерсть там редкая)
    pink = np.clip(-N[:, 2] - 0.45, 0, 1) * np.clip((P[:, 1] + 0.02) / 0.06, 0, 1) * (1 - m)
    c = mix(c, col((0.80, 0.64, 0.62)), np.clip(pink * 1.3, 0, 0.7))
    return c


def paint_eyes(c, P, N):
    front = N[:, 1] < -0.05
    for ex, ez in EYES:
        sx = 1.0 if ex > 0 else -1.0
        d = np.hypot(P[:, 0] - ex, P[:, 2] - ez)
        socket = front & (d < EYE_R + 0.0035)
        c = np.where(socket[:, None], mix(c, col((0.015, 0.013, 0.013)), np.clip((EYE_R + 0.0035 - d) / 0.003, 0, 1) * 0.8), c)
        eye = front & (d < EYE_R)
        ix, iz, ir = ex - 0.0010 * sx, ez + 0.0006, EYE_R * 0.86                     # радужка чуть к носу
        di = np.hypot(P[:, 0] - ix, P[:, 2] - iz)
        corner = eye & ((P[:, 0] - ex) * sx > 0.0068) & (np.abs(P[:, 2] - ez + 0.0008) < 0.0032)
        c = np.where(eye[:, None], col((0.03, 0.025, 0.02)), c)
        c = np.where(corner[:, None], col((0.72, 0.66, 0.62)), c)                    # белок — только в наружном уголке
        iris = eye & (di < ir) & ~corner
        g = np.clip(di / ir, 0, 1)
        c = np.where(iris[:, None], mix(col((0.20, 0.11, 0.05)), col((0.05, 0.03, 0.02)), g ** 1.4), c)
        c = np.where((eye & (di < ir * 0.55))[:, None], col((0.012, 0.010, 0.010)), c)
        rim = eye & (d > EYE_R - 0.0011)
        c = np.where(rim[:, None], col((0.02, 0.02, 0.02)), c)
        hl = eye & (np.hypot(P[:, 0] - ix + 0.0025 * sx, P[:, 2] - iz - 0.0035) < 0.0017)
        c = np.where(hl[:, None], col((0.75, 0.75, 0.74)), c)

    return c


def blaze_mask(P, N):
    """Белая проточина: от темени узкой полосой к стопу (сужается, кончается между глазами) и назад по
    макушке к затылку (там переходит в белую шею)."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    edge = (fbm(x * 260, z * 180 + y * 120, 93) - 0.5) * 0.006
    hw = 0.004 + 0.017 * np.clip((z - 0.356) / 0.042, 0, 1) ** 1.1          # лицо: снизу узкая, к темени шире
    hw = np.where(y > -0.215, 0.019 - 0.005 * np.clip((y + 0.215) / 0.04, 0, 1), hw)   # по макушке назад
    xc = 0.0015 + 0.003 * np.clip((z - 0.385) / 0.02, 0, 1)
    b = np.clip((hw - np.abs(x - xc + edge)) / 0.003, 0, 1)
    b = b * np.clip((z - 0.355) / 0.004, 0, 1)
    b = b * np.where(y > -0.215, np.clip((z - 0.385) / 0.008, 0, 1), 1.0)        # на затылке — только поверху
    return b


def paint_head(P, N):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    ax = np.abs(x)
    c = black_coat(P, N)
    # седина на морде: серая «соль с перцем» на морде и брылях, светлее к нижнему краю брылей
    fleck = vnoise(x * 2200, z * 2200 + y * 1500, 91)
    soft = fbm(x * 300, z * 300 + y * 200, 92)
    muzzle = np.clip((-0.262 - y) / 0.010, 0, 1) * np.clip((0.349 - z) / 0.012, 0, 1)
    jowl = np.clip((0.305 - z) / 0.020, 0, 1) * np.clip((-0.232 - y) / 0.02, 0, 1)
    g = np.clip((0.42 * muzzle + 0.50 * jowl) * (0.75 + 0.5 * soft) + (fleck - 0.5) * 0.30 * np.maximum(muzzle, jowl), 0, 0.8)
    c = mix(c, col((0.50, 0.49, 0.48)), g)
    # проточина
    b = blaze_mask(P, N)
    c = mix(c, white_coat(P) * 0.98, b)
    # переход к белой шее: только снизу на затылке и по горлу — голова остаётся чёрной
    throat = np.clip((0.300 - z) / 0.016, 0, 1) * np.clip((y + 0.205) / 0.015, 0, 1)
    c = mix(c, white_coat(P), throat * 0.9)
    front = N[:, 1] < -0.2
    # складка над носом: тёмная бороздка под валиком и блик на валике
    groove = np.exp(-((z - 0.3545) / 0.0018) ** 2) * (ax < 0.034) * front
    c = mix(c, col((0.005, 0.005, 0.005)), 0.9 * groove)
    roll = np.exp(-((z - 0.3495) / 0.0025) ** 2) * (ax < 0.030) * front
    c = mix(c, col((0.40, 0.39, 0.38)), 0.55 * roll)
    # стоп — глубокая тёмная складка
    stop = np.exp(-((z - 0.360) / 0.005) ** 2) * np.exp(-(x / 0.006) ** 2) * front
    c = mix(c, col((0.005, 0.005, 0.005)), 0.7 * stop)
    # нос: широкая плоская мочка с ноздрями и бликом
    nose = front & ((((x - NOSE[0]) / 0.019) ** 2 + ((z - NOSE[1]) / 0.0105) ** 2) < 1.0) & (y < -0.274)
    c = np.where(nose[:, None], col((0.035, 0.033, 0.035)) * (0.85 + 0.3 * vnoise(x * 2000, z * 2000, 95))[:, None], c)
    for sx in (-1, 1):
        nos = nose & (np.hypot((x - 0.0095 * sx) * 1.2, (z - NOSE[1] + 0.003) * 1.8) < 0.0052)
        c = np.where(nos[:, None], col((0.004, 0.004, 0.004)), c)
    hl = nose & (np.hypot(x + 0.004, z - NOSE[1] - 0.006) < 0.0035)
    c = np.where(hl[:, None], col((0.17, 0.17, 0.18)), c)
    phil = front & (ax < 0.0016) & (z > 0.303) & (z < NOSE[1] - 0.008)
    c = mix(c, col((0.02, 0.02, 0.02)), phil.astype(np.float32) * 0.8)
    # линия рта по краю брылей, тёмная губа
    mz = 0.313 - 0.030 * np.clip(ax / 0.050, 0, 1) ** 1.4
    mouth = (front & (np.abs(z - mz) < 0.0018) & (ax < 0.056)).astype(np.float32)
    c = mix(c, col((0.02, 0.018, 0.018)), mouth * 0.85)
    c = paint_eyes(c, P, N)
    return c


def paint_ear(tag, P, N):
    sx = np.where(P[:, 0] >= 0, 1.0, -1.0)
    out = []
    for s in (1, -1):
        base, up, nrm, side = ear_frame(s)
        out.append((np.array(base), np.array(up), np.array(side)))
    bl, ul, sl = out[0]; br, ur, sr = out[1]
    L = (sx > 0)[:, None]
    base = np.where(L, bl, br); up = np.where(L, ul, ur); side = np.where(L, sl, sr)
    rel = P - base
    v = np.clip(((rel * up).sum(1) + 0.016) / EAR_H, 0, 1)
    hw = np.array([ear_hw(min(vv, 0.999)) for vv in np.linspace(0, 1, 64)])
    u = (rel * side).sum(1) / np.maximum(np.interp(v, np.linspace(0, 1, 64), hw), 1e-3)
    if tag == "ear_out":
        return black_coat(P, N) * 1.08
    skin = col((0.66, 0.53, 0.53)) * (0.92 + 0.14 * vnoise(u * 9, v * 9, 13))[:, None]
    cav = np.clip(1.0 - ((u / 0.70) ** 2 + ((v - 0.40) / 0.42) ** 2), 0, 1)         # тень в глубине раковины
    c = mix(skin, col((0.24, 0.17, 0.18)), cav ** 1.2 * 0.75)
    vein = np.exp(-((u - 0.15 * np.sin(v * 7)) / 0.05) ** 2) * (v > 0.3) * (v < 0.85)
    c = mix(c, col((0.55, 0.38, 0.40)), vein * 0.25)
    hair = np.clip((np.abs(u) - 0.72) / 0.18, 0, 1)                               # тёмный край раковины
    c = mix(c, black_coat(P, N), hair)
    c = mix(c, black_coat(P, N), np.clip((0.20 - v) / 0.14, 0, 1))                 # шерсть у основания
    return c


def paint_lid(P, N):
    """Закрытый глаз: чёрное веко, по нижней трети — дуга-щёлка с ресницами. Края — альфой по эллипсу."""
    x, z = P[:, 0], P[:, 2]
    ex = np.where(x >= 0, EYES[1][0], EYES[0][0]); ez = EYES[0][1]
    dx, dz = (x - ex) / LID_R[0], (z - ez) / LID_R[1]
    e = dx ** 2 + dz ** 2
    alpha = (e < 1.0).astype(np.float32)
    c = mix(black_coat(P, N), col((0.16, 0.15, 0.15)), np.clip(0.3 - 0.3 * e, 0, 0.3))
    slit = -0.20 - 0.16 * (1 - np.clip(dx, -1, 1) ** 2)
    line = np.clip(1 - np.abs(dz - slit) / 0.10, 0, 1) * np.clip((0.92 - np.abs(dx)) / 0.15, 0, 1)
    c = mix(c, col((0.005, 0.004, 0.004)), line)
    return c, alpha


def paint_paw(P, N, sx_paw):
    c = white_coat(P) * col((0.98, 0.97, 0.95))
    t = ticks(P, 0.010, 0.55, 0.0010, 0.0026, 15)
    c = mix(c, col((0.06, 0.06, 0.06)), t * 0.85)
    # бороздки между пальцами (по той же волне, что и геометрия) и когти
    xn = np.clip((P[:, 0] - sx_paw) / 0.021, -1, 1)
    toe = np.abs(np.sin(2 * np.pi * xn))
    grooves = (toe < 0.25) & (P[:, 2] > 0.004)
    c = c * np.where(grooves, 0.55, 1.0)[:, None]
    nail = (P[:, 2] < 0.009) & (P[:, 2] > 0.003) & (toe > 0.75) & (np.abs(N[:, 1]) > 0.55)
    c = np.where(nail[:, None], col((0.20, 0.18, 0.17)), c)
    pad = np.clip(-N[:, 2] - 0.5, 0, 1) * 2
    c = mix(c, col((0.16, 0.13, 0.13)), np.clip(pad, 0, 0.95))
    return c


def paint_collar(P, N, u, v):
    base = col((0.92, 0.38, 0.07)) * (0.92 + 0.10 * vnoise(u * 60, v * 4, 101))[:, None]
    edge = np.clip(np.abs(v - 0.5) * 2 - 0.62, 0, 1) * 2.2
    c = base * (1 - 0.40 * edge)[:, None]
    stitch = (np.abs(np.abs(v - 0.5) - 0.30) < 0.04) & ((u * 140) % 1.0 < 0.55)
    c = c * np.where(stitch, 0.82, 1.0)[:, None]
    # пряжка — на левом боку внизу: металлическая рамка со шпеньком
    p0, (rs, ru) = neck_at(0.48)
    d = np.array(NECK[1] - NECK[0], np.float32); d /= np.linalg.norm(d)
    upv = np.array((0, -1, 0), np.float32); upv = upv - d * upv.dot(d); upv /= np.linalg.norm(upv)
    rel = P - np.array(p0, np.float32)
    ang = np.arctan2(rel[:, 0], rel @ upv)                       # 0 — вперёд-вниз, +90° — левый бок
    du = (ang - math.radians(70)) * 0.07
    dv = v - 0.5
    frame = (np.abs(du) < 0.0085) & (np.abs(dv) < 0.62)
    hole = (np.abs(du) < 0.0055) & (np.abs(dv) < 0.36)
    metal = col((0.62, 0.58, 0.50)) * (0.8 + 0.4 * np.clip(N[:, 2] * 0.5 + 0.5, 0, 1))[:, None]
    c = np.where((frame & ~hole)[:, None], metal, c)
    c = np.where((hole & (np.abs(dv) < 0.06))[:, None], metal * 0.9, c)          # шпенёк
    c = np.where((frame & hole & (np.abs(dv) >= 0.06))[:, None], c * 0.55, c)
    light = 0.86 + 0.20 * np.clip(N[:, 2] * 0.5 + 0.5, 0, 1)
    return c * light[:, None]


def paint(tag, refs, P, N, LUV):
    n = len(P); alpha = np.ones(n, np.float32)
    u, v = LUV[:, 0], LUV[:, 1]
    ao = 0.40 + 0.60 * _AO ** 1.3 if _AO is not None else 1.0
    if tag in ("head", "ear_in", "ear_out", "lid"):
        P = hx_inv(P)
    if tag == "head":
        c = finish(paint_head(P, N), P, N)
    elif tag in ("body", "leg_r", "leg_f"):
        c = finish(coat(P, N, 0.45 if tag != "body" else 0.30), P, N)
    elif tag == "neck":
        c = finish(coat(P, N, 0.12), P, N)
        # складки под ошейником и под челюстью — тёмные полосы
        fold = np.zeros(n, np.float32)
        for t in (0.30, 0.58):
            p, _ = neck_at(t)
            dd = np.array(NECK[1] - NECK[0], np.float32); dd /= np.linalg.norm(dd)
            s = (P - np.array(p, np.float32)) @ dd
            fold = np.maximum(fold, np.exp(-((s - 0.009) / 0.004) ** 2))
        c = c * (1 - 0.12 * fold)[:, None]
    elif tag == "tail":
        c = finish(mix(white_coat(P), col((0.80, 0.66, 0.63)), 0.25), P, N)
    elif tag == "paw":
        sxp = np.where(P[:, 0] >= 0, 1.0, -1.0) * np.where(P[:, 1] < 0, 0.072, 0.073)
        c = finish(paint_paw(P, N, sxp), P, N, dirt_k=0.8)
    elif tag == "lid":
        c, alpha = paint_lid(P, N)
        c = finish(c, P, N)
    elif tag in ("ear_in", "ear_out"):
        c = paint_ear(tag, P, N)
        c = c * np.atleast_1d(ao)[:, None] if _AO is not None else c
        c = c * (0.80 + 0.25 * np.clip(N @ KEY * 0.5 + 0.5, 0, 1))[:, None]
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
    ys = [r[0] for r in T_ST]; zs = [r[4] for r in T_ST]
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
        n = eye_frame(ex, ez)[1]
        for vid, w in enumerate(mb.w):
            if w.get("Lid" + S_, 0) > 0.5 and vid in remap:
                mb.co[vid] = mb.co[vid] - n * LID_IN
                me.vertices[remap[vid]].co = mb.co[vid]
    me.update()


def lid_open_vec(S_):
    """Сдвиг кости века (в пространстве скелета) — выдвигает веко на глаз."""
    ex, ez = EYES[1 if S_ == "L" else 0]
    return tuple(eye_frame(ex, ez)[1] * LID_IN)


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
    """pose: кость → [(ось, градусы)] (оси скелета в покое) или готовый Quaternion в локальном пространстве кости."""
    pose = dict(pose)
    loc = pose.pop("_loc", {}); scl = pose.pop("_scl", {})
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        v = pose.get(pb.name, [])
        pb.rotation_quaternion = v if isinstance(v, Quaternion) else qw(arm, pb.name, v)
    for n in LOC_BONES:
        rq = arm.data.bones[n].matrix_local.to_quaternion()
        arm.pose.bones[n].location = rq.inverted() @ Vector(loc.get(n, (0, 0, 0)))
    for n in SCL_BONES:
        arm.pose.bones[n].scale = scl.get(n, (1, 1, 1))


# ---------- Сон (лист v2, «Resting pose»; фото на диване — hyuga_sleep_sofa_v2.webp) ----------
# Клубок на боку: грудь завалена на бок на 45°, таз — на 65°, хребет изогнут дугой к стороне лап (морда тянется к
# задним лапам). Голова почти прямо (уши стоят), повёрнута к зрителю и лежит подбородком на пледе и на нижней
# передней кисти; верхняя передняя лапа лежит на нижней. Задние сложены: нижняя — под крупом, верхняя — стопой
# вперёд вдоль живота. Всё, что внизу, касается пледа (замер — tools/blender/hyuga_bed_check.py). SLEEP_DOWN = "R" —
# лежит на правом боку (голова слева, спина от зрителя, как на фото); "L" — то же зеркально.
# Как строится (sleep_base):
#  1. хребет, шея и голова — по НАПРАВЛЕНИЯМ в пространстве скелета (вид сверху: «вперёд» — −Y, сторона лап при
#     SLEEP_DOWN = "R" — +X): куда смотрит кость, насколько опущена и насколько спина завалена к нижнему боку;
#  2. уровень пледа — низ туловища на деформированном меше; наклон шеи подбирается делением пополам так, чтобы
#     низ головы (подбородок, брыли) лёг на этот уровень (SLEEP_CHIN);
#  3. лапы ставятся в точки на пледе двухзвенным IK: у передних — запястье, у задних — скакательный сустав;
#     кисти, плюсны и стопы лежат подошвой на пледе.
#     Если толстый локоть или колено уходят под плед, сустав-середина поднимается, и IK решается заново.
# Сдвиг таза (SLEEP_LOC) подбирает fit_sleep: середина клубка над началом координат, нижняя точка на SLEEP_SINK
# в пледе. Проверка на диване из игры прямо в Blender — tools/blender/hyuga_bed_check.py.
SLEEP_L = 4.5
SLEEP_BREATH = 2.4      # сила дыхания во сне (множитель изгиба хребта и раздувания боков)
SLEEP_SINK = 0.006
SLEEP_LOC = (0.0, 0.0, 0.0)
SLEEP_DOWN = "R"
SLEEP_UP = "L" if SLEEP_DOWN == "R" else "R"
SLEEP_Q = {}            # локальные повороты костей в позе сна (считает fit_sleep)
SLEEP_AXX = {}          # ось X скелета в локальном пространстве каждой кости — для дыхания поверх позы
SLEEP_INFO = {}         # замеры подбора (для отчёта сборки)

# хребет: (поворот к стороне лап, наклон вниз, завал спины к нижнему боку), градусы; None — подбирается:
# у таза — чтобы круп лёг на плед вровень с грудью, у шеи — чтобы на плед лёг подбородок
SLEEP_AXIS = {"Hips": (-45, None, 65), "Spine1": (-15, 0, 55), "Spine2": (20, 0, 45), "Neck": (70, None, 25)}
SLEEP_HEAD = (110, 20, 15)      # морда: поворот к стороне лап, нос вниз, завал макушки к нижнему боку
SLEEP_CHIN = 0.0                # низ головы над уровнем пледа, м
SLEEP_TAIL = (0.5, 0.75, -0.4)  # хвостик прижат к стороне лап (x — к стороне лап, y — назад, z — вверх)
SLEEP_EARS = -12                # уши во сне расслаблены — откинуты назад, °
# Лапы: (нижняя, верхняя). Точки задаются от корня лапы (плечевой / тазобедренный сустав), опущенного на плед:
# (вперёд, к стороне лап, высота над пледом), метры, по направлению груди (передние) или таза (задние).
# mid — локоть / колено (куда сгибается сустав), end — запястье / скакательный сустав. turn — поворот кисти / стопы
# от того же направления к стороне лап, °.
SLEEP_FRONT = ({"mid": (-0.02, 0.03, 0.045), "end": (0.06, 0.06, 0.030), "turn": 40},     # нижняя: кисть под подбородком
               {"mid": (0.00, 0.05, 0.070), "end": (0.08, 0.04, 0.060), "turn": 50})      # верхняя: лежит на нижней
SLEEP_REAR = ({"mid": (0.08, 0.04, 0.045), "end": (-0.05, 0.02, 0.024), "turn": 30},       # нижняя: сложена под крупом
              {"mid": (0.11, 0.06, 0.060), "end": (-0.025, 0.07, 0.030), "turn": 10})     # верхняя: стопой вдоль живота
HEEL_H = 0.022                  # высота пятки над пледом, когда стопа лежит подошвой


def sleep_base(arm, body):
    """Локальные повороты костей (Quaternion) в позе сна — см. комментарий выше. Ставит скелет в позу (без сдвига)."""
    s = -1.0 if SLEEP_DOWN == "L" else 1.0
    D, U = SLEEP_DOWN, SLEEP_UP
    bones = arm.data.bones
    I3 = Matrix.Identity(3)
    Z = Vector((0, 0, 1))
    R = {}                                            # поворот каждой кости от покоя (пространство скелета)

    def V(x, y, z):                                   # вектор в пространстве скелета (с зеркалом)
        return Vector((x * s, y, z)).normalized()

    def fwd(yaw, pitch=0.0):                          # «вперёд», повёрнутое к стороне лап на yaw°, вниз на pitch°
        a, p = math.radians(yaw), math.radians(pitch)
        return V(math.sin(a) * math.cos(p), -math.cos(a) * math.cos(p), -math.sin(p))

    def side(yaw):                                    # горизонталь к стороне лап для направления yaw
        a = math.radians(yaw)
        return V(math.cos(a), math.sin(a), 0.0)

    def dors(yaw, roll):                              # «спина вверх», заваленная к нижнему боку на roll°
        a, r = math.radians(yaw), math.radians(roll)
        return V(-math.cos(a) * math.sin(r), -math.sin(a) * math.sin(r), math.cos(r))

    def frame(a, b):
        a = a.normalized(); b = (b - a * a.dot(b)).normalized()
        return Matrix((a, b, a.cross(b))).transposed()

    def orient(n, a0, b0, a, b):                      # поворот, переводящий пару (a0, b0) покоя в (a, b)
        R[n] = frame(a, b) @ frame(a0, b0).inverted()

    def rdir(n):
        return (bones[n].tail_local - bones[n].head_local).normalized()

    def aim(n, d):                                    # кость смотрит в d; без скручивания относительно родителя
        P = R[bones[n].parent.name]
        R[n] = (P @ rdir(n)).rotation_difference(d.normalized()).to_matrix() @ P

    def sole(n, d):                                   # кисть/стопа: носок в d (по горизонтали), подошва вниз
        orient(n, Vector((0, -1, 0)), Vector((0, 0, -1)), d, Vector((0, 0, -1)))

    def pos(n):                                       # голова кости в позе (до сдвига таза)
        b = bones[n]
        if not b.parent:
            return b.head_local.copy()
        return pos(b.parent.name) + R[b.parent.name] @ (b.head_local - b.parent.head_local)

    def length(n1, n2):
        return (bones[n2].head_local - bones[n1].head_local).length

    def ik(n1, n2, n3, target, mid):
        """Двухзвенный IK: n1 и n2 так, чтобы голова n3 пришла в target, средний сустав — как можно ближе к mid."""
        A = pos(n1); l1, l2 = length(n1, n2), length(n2, n3)
        pole = mid - A
        d = target - A; want = d.length
        L = min(max(want, abs(l1 - l2) + 1e-4), l1 + l2 - 1e-4); nd = d.normalized()
        pp = (pole - nd * pole.dot(nd)).normalized()
        a = (l1 * l1 - l2 * l2 + L * L) / (2 * L); h = math.sqrt(max(l1 * l1 - a * a, 0.0))
        M = A + nd * a + pp * h
        aim(n1, M - A); aim(n2, A + nd * L - M)
        return round((want - L) * 1000)               # недотянулся, мм

    def quats():
        Q, RR = {}, dict(R)
        for b in bones:                               # родители раньше детей (порядок BONES)
            Rn = RR.setdefault(b.name, RR[b.parent.name] if b.parent else I3)
            Rp = RR[b.parent.name] if b.parent else I3
            B = b.matrix_local.to_3x3()
            Q[b.name] = (B.inverted() @ Rp.inverted() @ Rn @ B).to_quaternion()
        for S_ in "LR":
            Q["Ear" + S_] = Q["Ear" + S_] @ qw(arm, "Ear" + S_, [("x", SLEEP_EARS)])
        return Q

    gname = {g.index: g.name for g in body.vertex_groups}
    dom = [gname[max(v.groups, key=lambda g: g.weight).group] if len(v.groups) else "" for v in body.data.vertices]
    rest_z = [v.co.z for v in body.data.vertices]

    def zmin(names, above=-1.0):                      # низ меша у вершин, где главная кость из names (и в покое выше above)
        Q = quats()
        for pb in arm.pose.bones:
            pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = Q[pb.name]
            pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
        bpy.context.view_layer.update()
        ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        me = ev.to_mesh()
        co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co)
        ev.to_mesh_clear()
        z = co.reshape(-1, 3)[:, 2]
        return float(min(z[i] for i, n in enumerate(dom) if n in names and rest_z[i] > above))

    def bisect(f, lo, hi, n=14):                      # f(lo) > 0 ≥ f(hi), f убывает
        for _ in range(n):
            mid = (lo + hi) / 2
            if f(mid) > 0:
                lo = mid
            else:
                hi = mid
        return hi

    # 1. хребет и голова
    pitch_of = {"Hips": 0.0, "Neck": 0.0}

    def axial():
        for n, (yaw, pitch, roll) in SLEEP_AXIS.items():
            orient(n, rdir(n), Z, fwd(yaw, pitch_of[n] if pitch is None else pitch), dors(yaw, roll))
        yaw, pitch, roll = SLEEP_HEAD
        orient("Head", Vector((0, -1, 0)), Z, fwd(yaw, pitch), dors(yaw, roll))
        aim("Tail", V(*SLEEP_TAIL))

    # 2. наклон таза (круп вровень с грудью), уровень пледа, наклон шеи (подбородок на плед).
    #    Круп лежит на боку бедра, поэтому к нему считается и верх нижнего бедра (в покое выше 15 см).
    rear = ("Hips", "Tail", "Thigh" + D)

    def rear_minus_front(p):
        pitch_of["Hips"] = p; axial()
        return zmin(rear, 0.15) - zmin(("Spine2", "Chest"))
    pitch_of["Hips"] = bisect(rear_minus_front, 40.0, -40.0)
    axial()
    zg = min(zmin(rear, 0.15), zmin(("Hips", "Spine1", "Spine2", "Chest", "Belly", "Tail")))

    def head_above(p):
        pitch_of["Neck"] = p; axial()
        return zmin(("Head",)) - (zg + SLEEP_CHIN)
    pitch_of["Neck"] = bisect(head_above, -20.0, 80.0)
    axial()
    SLEEP_INFO.clear()
    SLEEP_INFO["pitch"] = {k: round(v, 1) for k, v in pitch_of.items()}

    # 3. лапы. Сустав-середина (локоть, колено) толстый: если меш лапы уходит под плед, середина поднимается на
    #    недостающее и IK решается заново (до 6 раз).
    def spot(root, yaw, f, sd, h):                     # точка от корня лапы, опущенного на плед
        A = pos(root)
        return Vector((A.x, A.y, zg)) + fwd(yaw) * f + side(yaw) * sd + Z * h

    def place(S_, k, front, lift):
        if front:
            f, cy = SLEEP_FRONT[k], SLEEP_AXIS["Spine2"][0]
            mid = spot("Shoulder" + S_, cy, *f["mid"]) + Z * lift
            m = ik("Shoulder" + S_, "Forearm" + S_, "Paw" + S_, spot("Shoulder" + S_, cy, *f["end"]), mid)
            sole("Paw" + S_, fwd(cy + f["turn"]))
            return m
        r, hy = SLEEP_REAR[k], SLEEP_AXIS["Hips"][0]
        mid = spot("Thigh" + S_, hy, *r["mid"]) + Z * lift
        m = ik("Thigh" + S_, "Shin" + S_, "Hock" + S_, spot("Thigh" + S_, hy, *r["end"]), mid)
        H = pos("Hock" + S_)
        lh = length("Hock" + S_, "Foot" + S_); dz = (zg + HEEL_H) - H.z
        heel = H + fwd(hy + r["turn"]) * math.sqrt(max(lh * lh - dz * dz, 0.0)) + Z * dz
        aim("Hock" + S_, heel - H)
        sole("Foot" + S_, fwd(hy + r["turn"]))
        return m

    miss, lifts = {}, {}
    for S_, k in ((D, 0), (U, 1)):
        for front, names in ((True, ("Shoulder", "Forearm")), (False, ("Thigh", "Shin", "Hock"))):
            key = ("front" if front else "rear") + S_
            lift = 0.0
            for _ in range(6):
                miss[key] = place(S_, k, front, lift)
                below = zg - zmin(tuple(n + S_ for n in names))
                if below < 0.002:
                    break
                lift += below + 0.002
            lifts[key] = round(lift * 1000)
    SLEEP_INFO["mid_lift_mm"] = lifts
    SLEEP_INFO["ik_miss_mm"] = miss
    Q = quats()
    zmin(("Hips",))                                   # оставить скелет в позе
    return Q


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
    p = dict(SLEEP_Q)
    b = breath_curve(t, L) * SLEEP_BREATH
    b2 = breath_curve(t - 0.18, L) * SLEEP_BREATH                   # живот чуть отстаёт от груди
    for n, deg in (("Spine1", -0.7 * b2), ("Spine2", -0.6 * b), ("Neck", 0.5 * b), ("Head", -0.35 * b)):
        p[n] = p[n] @ Quaternion(SLEEP_AXX[n], math.radians(deg))    # изгиб в собственной плоскости кости
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
    global SLEEP_LOC, SLEEP_Q, SLEEP_AXX
    reset_pose(arm)
    SLEEP_Q = sleep_base(arm, body)
    SLEEP_AXX = {b.name: b.matrix_local.to_quaternion().inverted() @ Vector((1, 0, 0)) for b in arm.data.bones}
    p = dict(SLEEP_Q)
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
    return dict(SLEEP_INFO, loc=[round(float(v), 4) for v in SLEEP_LOC], size=[round(float(v), 3) for v in (mx - mn)])


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


PREVIEW_VIEWS = [  # имя, направление на камеру — как виды листа v2 (+ 3/4)
    ("side_right", (-1, 0, 0.05)), ("side_left", (1, 0, 0.05)), ("front", (0, -1, 0.05)),
    ("back", (0, 1, 0.05)), ("q34", (0.7, -1, 0.35)),
]


SLEEP_VIEWS = [  # поза сна: со стороны морды сверху-сбоку ≈45° (как «Resting pose» листа), сверху, со спины
    ("sleep_ref", (1.0, 1.0, 1.1)), ("sleep_top", (0.0, 0.0, 1.0)), ("sleep_back", (-1.0, -1.0, 0.8)),
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
    dens = {"head": 2.6, "body": 1.0, "neck": 1.1, "collar": 1.2, "tail": 0.9}
    for S_ in "LR":
        dens.update({"ear" + S_: 1.7, "f_paw" + S_: 1.5, "r_paw" + S_: 1.4, "lid" + S_: 3.5,
                     "f_leg" + S_: 1.1, "r_leg" + S_: 1.0})
    Y["ISL_DENS"] = {k: v * DENS_K for k, v in dens.items()}   # упаковщик ищет плотность до 500 px/м — для 1024 мало
    Y["paint"] = paint
    mb = build_all()
    D, pos = Y["pack_islands"](mb, size=ATLAS, pad=3)
    img = bpy.data.images.get(TEX_NAME)
    mats = [Y["make_material"]("HyugaFur", img, False), Y["make_material"]("HyugaEar", img, True)]
    body, fsel, used = Y["make_object"](mb, 0, "HyugaMesh", sc.collection, mats)
    info = {"tris": sum(len(mb.faces[f]) - 2 for f in fsel), "verts": len(used), "atlas": ATLAS,
            "density_px_per_m": round(D * DENS_K, 1)}

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
