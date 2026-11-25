# -*- coding: utf-8 -*-
# Марго (YUR-26): low-poly модель в стиле PS2 по референсам docs/references/margo/.
#
# Референсы:
#   margo_turnaround.png — ГЛАВНЫЙ для телосложения и одежды: вид спереди / сбоку / сзади (лицо спереди размыто);
#   margo_face_art.png   — ГЛАВНЫЙ для лица: рисунок анфас (глаза с тёмными кругами, тёмно-красные губы, заколка);
#   margo_photo.png      — живое фото: септум-кольцо в носу, бледная кожа, платиновые волосы.
#
# Как устроено (пайплайн Юрчика и Сергея: build_yurchik_v3.py, build_sergey_v2.py):
#   * сечения сняты с тёрнэраунда в пикселях и переведены в метры: 1 px = T_S м, земля — строка T_GY,
#     центры видов спереди / сбоку / сзади — T_CXF / T_CXS / T_CXB;
#   * одежда: бомбер нараспашку с меховой подкладкой и капюшоном на спине, под ним водолазка в розово-чёрную
#     полоску и ремень, узкие джинсы, массивные ботинки на платформе;
#   * голова на тёрнэраунде маленькая (≈ 8.8 «голов» в росте) — модель берёт её крупнее в HEAD_SCALE раз
#     (вокруг основания шеи), чтобы рядом с Юрчиком она не выглядела булавочной; черты лица — гладкие «бугры»;
#   * текстура 512 (атлас персонажа PS2): одежда — проекция тёрнэраунда по нормали, лицо — проекция рисунка
#     анфас, волосы и водолазка на шее — процедурно; свет «запечён», как в играх той эпохи;
#   * скелет — те же 15 костей, что у Сергея и офников (свои положения суставов), анимации Quaternius UAL (CC0).
#
# Запуск — ТОЛЬКО в открытом Blender (через Blender MCP или вкладку Scripting), без temp_override:
#   exec(open(r"C:\Users\mrs\Documents\yuranchik_game\tools\blender\build_margo.py", encoding="utf-8").read(),
#        {"YUR_ROOT": r"C:\Users\mrs\Documents\yuranchik_game", "YUR_STAGE": "geo"})
# YUR_STAGE: "geo" — сетка; "tex" — + текстура; "full" — + скелет, анимации, экспорт assets/models/margo.gltf
# и копия сцены в tools/blender/margo.blend. YUR_PREVIEW = папка — сохранить превью-рендеры туда.
# Оси Blender: Z вверх, персонаж смотрит в -Y (в Godot это +Z), левая сторона персонажа — +X.
import bpy, os, math, importlib, sys
import numpy as np
from mathutils import Vector, Quaternion

ROOT = globals().get("YUR_ROOT", r"C:\Users\mrs\Documents\yuranchik_game")
STAGE = globals().get("YUR_STAGE", "full")
PREVIEW = globals().get("YUR_PREVIEW")
HERE = os.path.join(ROOT, "tools", "blender")
REF_DIR = os.path.join(ROOT, "docs", "references", "margo")
SCENE = "Margo"
NAME = "Margo"
ATLAS = 512

# --- тёрнэраунд: 1 px = T_S м, земля — строка T_GY, макушка — T_TOP; центры видов по X ---
T_HEIGHT = 1.65
T_GY, T_TOP = 692.0, 21.0
T_S = T_HEIGHT / (T_GY - T_TOP)
T_CXF, T_CXS, T_CXB = 218.0, 655.0, 1075.0
# --- рисунок лица: центр лица по X, строка глаз, м на px (до увеличения головы) ---
ART_CX, ART_EY = 207.0, 225.0
EYE_Z = 1.534                                   # глаза на тёрнэраунде (вид сбоку, строка 68)
ART_K = 0.049 / 87.0                            # глаза→рот: 87 px рисунка = 0.049 м тёрнэраунда
HEAD_SCALE = 1.10                               # голова крупнее, чем на тёрнэраунде
PIV = Vector((0.0, -0.010, 1.400))              # центр увеличения головы — основание шеи
HYC = 0.0                                       # центр головы по Y (до увеличения)


def load(name, cut):
    src = open(os.path.join(HERE, name), encoding="utf-8").read()
    ns = {"YUR_ROOT": ROOT, "__file__": os.path.join(HERE, name)}
    exec(compile(src[:src.rindex(cut)], name, "exec"), ns)
    return ns


E = load("build_enemies.py", "\nmain()")              # грузит Юрчика (Y, простые кисти) и перенос анимаций (R)
Y, R = E["Y"], E["R"]
MB, loft, ngon, dark_cap, sellipse, mx = Y["MB"], Y["loft"], Y["ngon"], Y["dark_cap"], Y["sellipse"], Y["mx"]
rad, clamp, lerp, smooth, sgnpow = Y["rad"], Y["clamp"], Y["lerp"], Y["smooth"], Y["sgnpow"]
col, fbm, vnoise = Y["col"], Y["fbm"], Y["vnoise"]
toplight, mix, nsmooth = E["toplight"], E["mix"], E["nsmooth"]
Y["ATLAS"] = ATLAS

CLIPS = [
    ("Idle", "UAL1", "Idle_Loop", False),
    ("Walk", "UAL1", "Walk_Loop", False),
    ("Run", "UAL1", "Jog_Fwd_Loop", False),
]


def hx(p, t=1.0):
    """Увеличение головы вокруг основания шеи (t — доля: 1 — полностью, 0 — без изменения)."""
    p = Vector(p)
    return PIV + (p - PIV) * (1.0 + (HEAD_SCALE - 1.0) * t)


def unhx(P):
    """Обратное к hx (t = 1) для массива точек — для раскраски головы и волос по референсам."""
    piv = np.array(PIV, np.float32)
    return piv + (P - piv) / HEAD_SCALE


# =====================================================================================
#  Скелет: суставы Марго (метры)
# =====================================================================================
JS = Vector((0.150, 0.005, 1.315))                       # плечевой сустав (левый)
AD = Vector((0.175, 0.0, -0.475)).normalized()           # ось руки в A-позе (руки ближе к телу, чем у Юрчика)
AN = Vector((-AD.z, 0.0, AD.x))                          # перпендикуляр «вверх-наружу»
ELBOW_T, WRIST_T = 0.270, 0.455                  # запястье в рукаве: манжета (до t = 0.508) закрывает полкисти


def make_bones():
    b = [("Pelvis", (0, -0.015, 0.875), (0, -0.015, 0.985), None),
         ("Spine", (0, -0.012, 0.985), (0, -0.006, 1.360), "Pelvis"),
         ("Head", tuple(hx((0, -0.012, 1.405))), tuple(hx((0, -0.004, 1.630))), "Spine")]
    for s, sx in (("L", 1), ("R", -1)):
        el = JS + AD * ELBOW_T + Vector((0, 0.004, 0)); wr = JS + AD * WRIST_T + Vector((0, -0.018, 0))
        b += [("UpperArm" + s, tuple(mx(JS, sx)), tuple(mx(el, sx)), "Spine"),
              ("Forearm" + s, tuple(mx(el, sx)), tuple(mx(wr, sx)), "UpperArm" + s),
              ("Hand" + s, tuple(mx(wr, sx)), tuple(mx(wr + Vector((0.024, -0.012, -0.090)), sx)), "Forearm" + s),
              ("Thigh" + s, (0.085 * sx, -0.020, 0.865), (0.093 * sx, -0.008, 0.475), "Pelvis"),
              ("Shin" + s, (0.093 * sx, -0.008, 0.475), (0.113 * sx, 0.018, 0.105), "Thigh" + s),
              ("Foot" + s, (0.113 * sx, 0.018, 0.105), (0.135 * sx, -0.115, 0.035), "Shin" + s)]
    return b


# =====================================================================================
#  Торс: бомбер нараспашку (колонки 'j') + водолазка, ремень и джинсы в просвете (колонки 'h')
# =====================================================================================
M_COLS = [("c0", 0, 'h'), ("hL", 22, 'h'), ("jL", 22, 'j'), ("L45", 45, 'j'), ("L67", 67.5, 'j'), ("L90", 90, 'j'),
          ("L112", 112.5, 'j'), ("L137", 137, 'j'), ("L160", 160, 'j'), ("b", 180, 'j'),
          ("R160", -160, 'j'), ("R137", -137, 'j'), ("R112", -112.5, 'j'), ("R90", -90, 'j'), ("R67", -67.5, 'j'),
          ("R45", -45, 'j'), ("jR", -22, 'j'), ("hR", -22, 'h')]
M_IDX = {c[0]: i for i, c in enumerate(M_COLS)}
# z, полуширина a, вперёд bf, назад bb, центр yc, «квадратность» n, глубина водолазки/джинсов в просвете,
# полуширина просвета у края подкладки. Снято с тёрнэраунда: спереди куртка ±69 px (подол) .. ±77 px (резинка),
# сбоку перед куртки ~690 px, спина ~594 px; грудь в водолазке выступает до 697 px.
M_RINGS = [
    (1.400, 0.070, 0.060, 0.075, 0.005, 2.0, -0.052, 0.020),   # 0 ворот (под мехом капюшона)
    (1.360, 0.150, 0.085, 0.110, 0.020, 2.3, -0.074, 0.050),   # 1 плечи
    (1.300, 0.165, 0.105, 0.120, 0.025, 2.6, -0.094, 0.058),
    (1.250, 0.168, 0.112, 0.125, 0.028, 2.6, -0.103, 0.060),   # 3 грудь
    (1.195, 0.170, 0.115, 0.127, 0.030, 2.6, -0.098, 0.060),   # 4 подмышка
    (1.100, 0.172, 0.117, 0.128, 0.032, 2.6, -0.086, 0.060),
    (1.000, 0.176, 0.118, 0.130, 0.032, 2.6, -0.088, 0.062),   # 6 ремень
    (0.905, 0.185, 0.118, 0.128, 0.030, 2.6, -0.096, 0.064),   # 7 верх резинки
    (0.850, 0.172, 0.110, 0.118, 0.025, 2.6, -0.100, 0.062),   # 8 подол
]


def torso_w(z, x=0.0):
    if z >= 1.10:
        return {"Spine": 1.0}
    wp = 0.8 * smooth((1.10 - z) / 0.20)
    if z >= 0.90:
        return {"Spine": 1.0 - wp, "Pelvis": wp}
    k = 0.35 * smooth((0.92 - z) / 0.08)
    side = clamp(x / 0.08, -1, 1)
    return {"Spine": (1 - wp) * (1 - k), "Pelvis": wp * (1 - k), "ThighL": k * (0.5 + 0.5 * side),
            "ThighR": k * (0.5 - 0.5 * side)}


def build_torso(mb):
    rings = []
    for i, (z, a, bf, bb, yc, n, yin, hx_) in enumerate(M_RINGS):
        ids = []
        for name, deg, layer in M_COLS:
            th = rad(deg)
            x, y = sellipse(a, bf, bb, yc, th, n)
            zz = z
            if i == 8:
                zz = z - 0.008 * max(0.0, math.cos(th)) ** 1.2
            if layer == 'h':
                x = 0.0 if name == "c0" else math.copysign(hx_, x)
                y = yin + (0.004 if name != "c0" else 0.0)
            ids.append(mb.vert((x, y, zz), torso_w(zz, x)))
        rings.append(ids)
    hole = {(M_IDX[a], M_IDX[b]) for a, b in (("L67", "L90"), ("L90", "L112"), ("R112", "R90"), ("R90", "R67"))}

    def skip(i, j0, j1):
        return i in (1, 2, 3) and (j0, j1) in hole

    def tagfn(i, j0, j1):
        la, lb = M_COLS[j0][2], M_COLS[j1][2]
        if la == 'h' and lb == 'h':
            return "inner"
        if la != lb:
            return "lining"
        return "jacket"

    loft(mb, rings, "torso", "jacket", seam=M_IDX["R90"], skip=skip, tagfn=tagfn, inside=Vector((0, 0.02, 1.15)))
    dark_cap(mb, rings[8], (0, 0.020, 0.86), 0.5, (0, 0, 0.03), (0, 0, -1))
    dark_cap(mb, rings[0], (0, 0.000, 1.40), 0.55, (0, 0, -0.010), (0, 0, 1))
    return rings


# =====================================================================================
#  Рукава (объёмные, с резинкой на манжете) и кисти — строители Юрчика с суставами Марго
# =====================================================================================
SLEEVE_M = [  # t и h верхней кромки, t и h нижней кромки (вдоль оси руки / поперёк), радиус по глубине, сдвиг по Y
    (0.060, 0.058, 0.150, -0.072, 0.066, 0.000),
    (0.150, 0.062, 0.250, -0.074, 0.070, 0.004),
    (0.255, 0.068, 0.320, -0.074, 0.071, 0.006),
    (0.350, 0.072, 0.390, -0.072, 0.069, 0.004),
    (0.425, 0.070, 0.445, -0.066, 0.064, 0.000),   # напуск над манжетой
    (0.452, 0.050, 0.462, -0.050, 0.050, -0.004),  # верх резинки манжеты
    (0.505, 0.047, 0.508, -0.047, 0.047, -0.008),  # край манжеты (кисть видна наполовину)
]
HAND_K = 0.80                                  # женская кисть меньше (из-под манжеты видна только половина)
HAND_M = [  # l, p, угол сгиба, полуширина, толщина к ладони / к тыльной стороне — расслабленная кисть
    (-0.030, 0.000, 0, 0.026, 0.016, 0.016),
    (0.020, 0.000, 0, 0.039, 0.014, 0.015),
    (0.062, 0.002, 0, 0.045, 0.013, 0.014),
    (0.094, 0.003, 6, 0.043, 0.011, 0.0125),
    (0.128, 0.010, 25, 0.040, 0.009, 0.0105),
    (0.158, 0.026, 50, 0.035, 0.008, 0.0085),
    (0.175, 0.045, 78, 0.030, 0.007, 0.007),
]


def setup_arm_globals():
    Y["JS"], Y["AD"], Y["AN"] = JS, AD, AN
    Y["ELBOW_T"], Y["WRIST_T"] = ELBOW_T, WRIST_T
    Y["SLEEVE"] = SLEEVE_M
    Y["T_COLS"] = M_COLS; Y["T_IDX"] = M_IDX
    hw = JS + AD * WRIST_T + Vector((0, -0.012, 0))
    hl = Vector((0.24, -0.06, -0.97)).normalized()
    hwd = Vector((-0.82, 0.57, 0.0)).cross(hl).normalized()
    Y["HAND_W"], Y["HAND_L"], Y["HAND_WD"], Y["HAND_PN"] = hw, hl, hwd, hl.cross(hwd).normalized()
    Y["HAND"] = [(l * HAND_K, p * HAND_K, a, w * HAND_K, tp * HAND_K, tb * HAND_K) for l, p, a, w, tp, tb in HAND_M]
    Y["THUMB"] = [(tuple(c * HAND_K for c in cc), r * HAND_K) for cc, r in
                  [((0.026, 0.036, 0.006), 0.0140), ((0.056, 0.054, 0.018), 0.0128), ((0.084, 0.050, 0.034), 0.0110)]]
    Y["THUMB_TIP"] = tuple(c * HAND_K for c in (0.100, 0.038, 0.044))


# =====================================================================================
#  Джинсы (узкие) и ботинки на платформе
# =====================================================================================
PYC = -0.018
P_RINGS_M = [(0.995, 0.138, 0.066, 0.082), (0.905, 0.158, 0.076, 0.098), (0.830, 0.168, 0.094, 0.106)]
CROTCH_Z = 0.778
LEG_M = [  # z, центр x, центр y, радиус по x, радиус по y (с тёрнэраунда; спереди — левая нога, сбоку — профиль)
    (0.735, 0.087, -0.027, 0.078, 0.083),
    (0.660, 0.089, -0.026, 0.068, 0.078),
    (0.590, 0.089, -0.023, 0.058, 0.068),
    (0.530, 0.089, -0.017, 0.052, 0.062),
    (0.472, 0.093, -0.008, 0.049, 0.060),   # колено
    (0.420, 0.100, 0.008, 0.053, 0.062),
    (0.374, 0.107, 0.019, 0.056, 0.064),    # икра
    (0.275, 0.112, 0.020, 0.044, 0.054),
    (0.200, 0.112, 0.016, 0.038, 0.050),    # щиколотка
    (0.150, 0.113, 0.013, 0.043, 0.056),
    (0.118, 0.114, 0.012, 0.047, 0.061),    # край джинсов на ботинке
]


def thigh_w(x, z):
    k = 0.9 * smooth((0.95 - z) / 0.2) * smooth(abs(x) / 0.1)
    if k <= 0:
        return {"Pelvis": 1.0}
    return {"Pelvis": 1 - k, ("ThighL" if x > 0 else "ThighR"): k}


def build_jeans(mb):
    rings = []
    for z, a, bf, bb in P_RINGS_M:
        pts, ws = [], []
        for j in range(16):
            x, y = sellipse(a, bf, bb, PYC, rad(22.5 * j), 2.4)
            pts.append((x, y, z)); ws.append(thigh_w(x, z))
        rings.append(mb.ring(pts, ws))
    loft(mb, rings, "pelvis", "jeans", seam=8)
    C = mb.vert((0, PYC, CROTCH_Z), {"Pelvis": 0.6, "ThighL": 0.2, "ThighR": 0.2})
    P2 = rings[-1]
    for sx in (1, -1):
        s = "L" if sx > 0 else "R"; TH, SH = "Thigh" + s, "Shin" + s
        loop = ([P2[j] for j in range(9)] if sx > 0 else [P2[(16 - j) % 16] for j in range(9)]) + [C]
        lr = [loop]
        for k, (z, cx, cy, rx, ry) in enumerate(LEG_M):
            wk = smooth((0.56 - z) / 0.15)
            pts, ws = [], []
            for j in range(10):
                ph = rad(-54 + 36 * j)
                pts.append((sx * (cx + rx * math.sin(ph)), cy - ry * math.cos(ph), z))
                if k == 0:
                    ws.append({TH: 0.75, "Pelvis": 0.25} if j in (0, 8, 9) else {TH: 1.0})
                else:
                    ws.append({TH: 1 - wk, SH: wk})
            lr.append(mb.ring(pts, ws))
        loft(mb, lr, "leg" + s, "jeans", seam=9)
        z, cx, cy = LEG_M[-1][0], LEG_M[-1][1], LEG_M[-1][2]
        dark_cap(mb, lr[-1], (sx * cx, cy, z), 0.5, (0, 0, 0.03), (0, 0, -1))


def setup_boot_globals():
    ang = rad(8)
    Y["BOOT_A"] = Vector((0.118, -0.022, 0.0)); Y["BOOT_ANG"] = ang
    Y["BOOT_F"] = Vector((math.sin(ang), -math.cos(ang), 0)); Y["BOOT_O"] = Vector((math.cos(ang), math.sin(ang), 0))
    Y["SOLE_Z"] = 0.040                                                       # толстая платформа (≈ 17 px)
    Y["SOLE_SPEC"] = (0.022, 0.140, 0.140, 0.062, 0.052, 3.0)                  # носок -0.182, пятка +0.095 (сбоку)
    Y["BOOT_SPEC"] = [
        (0.041, 0.022, 0.132, 0.134, 0.057, 0.047, 3.0),
        (0.060, 0.021, 0.130, 0.133, 0.057, 0.048, 3.0),     # борт
        (0.078, 0.012, 0.120, 0.126, 0.054, 0.047, 2.6),     # верх носка
        (0.095, -0.004, 0.098, 0.110, 0.050, 0.047, 2.4),    # подъём
        (0.112, -0.018, 0.068, 0.084, 0.046, 0.046, 2.3),    # шнуровка
        (0.128, -0.026, 0.048, 0.056, 0.042, 0.042, 2.2),    # верх ботинка (под краем джинсов)
        (0.165, -0.028, 0.040, 0.046, 0.036, 0.036, 2.0),
    ]


# =====================================================================================
#  Голова (до увеличения HEAD_SCALE), водолазка на шее, волосы, заколка
# =====================================================================================
HEAD_COLS = [0, 6, 12, 19, 27, 36, 47, 60, 75, 95, 120, 150, 180, -150, -120, -95, -75, -60, -47, -36, -27, -19, -12, -6]
H_M = [  # z спереди, z сзади, полуширина, глубина вперёд, назад (от HYC). Профиль — вид сбоку тёрнэраунда:
    # лоб 683 px -> -0.069, кончик носа 692 -> -0.091, подбородок 684 -> -0.071, затылок ~625 -> +0.074
    (1.454, 1.488, 0.014, 0.042, 0.044),     # под подбородком
    (1.460, 1.492, 0.026, 0.058, 0.048),
    (1.469, 1.496, 0.038, 0.066, 0.052),     # подбородок
    (1.478, 1.500, 0.046, 0.070, 0.056),     # нижняя губа
    (1.486, 1.505, 0.051, 0.072, 0.060),     # рот
    (1.493, 1.510, 0.054, 0.072, 0.064),     # верхняя губа
    (1.501, 1.515, 0.057, 0.071, 0.068),     # под носом
    (1.510, 1.522, 0.060, 0.070, 0.072),     # нос
    (1.520, 1.530, 0.062, 0.068, 0.075),     # скулы
    (1.531, 1.538, 0.063, 0.067, 0.078),     # глаза
    (1.540, 1.546, 0.064, 0.069, 0.079),
    (1.552, 1.556, 0.065, 0.070, 0.080),     # брови
    (1.570, 1.572, 0.065, 0.067, 0.080),     # лоб
    (1.592, 1.592, 0.063, 0.064, 0.077),
    (1.612, 1.612, 0.058, 0.058, 0.070),
    (1.628, 1.628, 0.048, 0.046, 0.058),
    (1.638, 1.638, 0.034, 0.030, 0.040),
]
EYE_X = 0.0236                                  # глаза на рисунке: 165 и 248 px (центр 207)


def g(x, s):
    return math.exp(-(x / s) ** 2)


def face_disp(x, z, th):
    """Смещение лица вперёд (fwd) и вверх (up), метры до увеличения головы."""
    ax = abs(x); front = max(0.0, math.cos(th)) ** 1.5
    fwd = 0.0; up = 0.0
    fwd -= 0.009 * smooth((ax - 0.030) / 0.035) * (1 - smooth((1.470 - z) / 0.02))      # бока лица уходят назад
    # нос: прямой, узкий; переносица -> кончик (+0.017 на 1.505), крылья, тень под носом
    mask = smooth((1.548 - z) / 0.010) * (1 - smooth((1.500 - z) / 0.006))
    fwd += (0.004 + 0.013 * smooth((1.534 - z) / 0.030)) * mask * g(ax, 0.008)
    fwd += 0.005 * g(ax - 0.011, 0.005) * g(z - 1.503, 0.005)
    fwd -= 0.002 * g(ax, 0.010) * g(z - 1.497, 0.003)
    # надбровья и глазницы
    fwd += 0.002 * g(z - 1.552, 0.006) * (1 - smooth((ax - 0.042) / 0.012))
    fwd -= 0.005 * g(ax - EYE_X, 0.011) * g(z - 1.534, 0.007)
    # скулы
    fwd += 0.005 * g(ax - 0.040, 0.012) * g(z - 1.520, 0.012)
    # полные губы: верхняя / нижняя, щель рта
    lip = 1 - smooth((ax - 0.016) / 0.005)
    fwd += 0.004 * g(z - 1.491, 0.004) * lip + 0.005 * g(z - 1.482, 0.004) * lip
    fwd -= 0.002 * g(z - 1.487, 0.002) * lip
    fwd -= 0.0015 * g(ax, 0.014) * g(z - 1.474, 0.003)                                  # ямка под губой
    fwd += 0.003 * g(ax, 0.014) * g(z - 1.466, 0.007)                                    # подбородок
    return fwd * front, up * front


def head_params(z, back=False):
    """Полуширина и глубины головы на высоте z (по профилю спереди)."""
    rows = H_M
    k = 0 if not back else 1
    if z <= rows[0][k]:
        r = rows[0]; return r[2], r[3], r[4]
    for i in range(len(rows) - 1):
        z0, z1 = rows[i][k], rows[i + 1][k]
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            return tuple(lerp(rows[i][j], rows[i + 1][j], t) for j in (2, 3, 4))
    r = rows[-1]; return r[2], r[3], r[4]


def head_xy(th, z, off=0.0):
    a, bf, bb = head_params(z)
    return sellipse(a + off, bf + off, bb + off, HYC, th, 2.2 if math.cos(th) > 0 else 2.0)


def build_head(mb):
    W = {"Head": 1.0}
    rings = []
    for zf, zb, a, bf, bb in H_M:
        pts = []
        for deg in HEAD_COLS:
            th = rad(deg)
            x, y = sellipse(a, bf, bb, HYC, th, 2.2 if math.cos(th) > 0 else 2.0)
            z = zf + (zb - zf) * (1 - math.cos(th)) / 2
            fwd, up = face_disp(x, z, th)
            pts.append(hx((x, y - fwd, z + up)))
        rings.append(mb.ring(pts, W))
    pole = mb.vert(hx((0, HYC + 0.004, 1.642)), W)

    def useg(j0, j1):                                  # затылок под волосами — мало текселей
        back = lambda j: math.cos(rad(HEAD_COLS[j])) < 0.0
        return 0.3 if back(j0) and back(j1) else 1.0

    loft(mb, rings, "head", "face", seam=HEAD_COLS.index(180), useg=useg, pole=pole)


def build_turtleneck(mb):
    """Шея в водолазке: от ворота куртки до подбородка; верх сзади уходит под волосы."""
    spec = [  # z спереди, z сзади, a, bf, bb, yc, вес Head
        (1.388, 1.388, 0.054, 0.054, 0.056, -0.004, 0.0),
        (1.415, 1.418, 0.047, 0.047, 0.050, -0.008, 0.3),
        (1.440, 1.452, 0.044, 0.045, 0.048, -0.012, 0.7),
        (1.456, 1.478, 0.045, 0.047, 0.049, -0.014, 1.0),   # отворот под подбородком
    ]
    rings = []
    for zf, zb, a, bf, bb, yc, wh in spec:
        pts = []
        for j in range(12):
            th = rad(30 * j)
            x, y = sellipse(a, bf, bb, yc, th, 2.1)
            z = zf + (zb - zf) * ((1 - math.cos(th)) / 2) ** 0.8
            pts.append(hx((x, y, z), smooth((z - 1.395) / 0.05)))
        rings.append(mb.ring(pts, {"Head": wh, "Spine": 1 - wh}))
    loft(mb, rings, "neck", "neck", seam=6)


# --- волосы: платиновое каре до плеч, прямой пробор; «шапочка» на черепе + «занавес» до плеч + пряди ---
HAIR_COLS = [0, 15, 30, 45, 60, 80, 105, 130, 155, 180, -155, -130, -105, -80, -60, -45, -30, -15]
# спереди «занавес» начинается за скулой: на виде сбоку профиль лица открыт (волосы с ~-0.02 м по Y и дальше назад),
# спереди волосы обрамляют лицо по бокам — пряди-карточки у висков
CUR_COLS = [70, 86, 105, 128, 154, 180, -154, -128, -105, -86, -70]
CUR_ROWS = [  # z, вынос от головы (низ — ниже подбородка: вокруг шеи, волосы ложатся на мех капюшона)
    (1.606, 0.013), (1.556, 0.020), (1.520, 0.031), (1.482, 0.045), (1.442, 0.058), (1.400, 0.066)]


def hairline_z(th):
    """Нижний край «шапочки» волос: прямой пробор — по центру лба линия волос выше (1.598), к вискам волосы
    спадают «домиком» и закрывают углы лба (1.545); за висками — под «занавесом»."""
    ad = abs(math.degrees(th))
    if ad < 44:
        return 1.598 - 0.053 * smooth((ad - 3) / 34)
    return 1.548


def hair_pt(th, z, off):
    """Точка волос: над головой — по её форме, ниже подбородка — вокруг шеи (эллипс)."""
    zz = max(z, 1.478)
    a, bf, bb = head_params(zz)
    k = smooth((1.478 - z) / 0.06)                       # ниже челюсти — переходим к эллипсу вокруг шеи
    a = lerp(a, 0.056, k); bf = lerp(bf, 0.058, k); bb = lerp(bb, 0.074, k)
    x, y = sellipse(a + off, bf + off, bb + off, HYC, th, 2.2 if math.cos(th) > 0 else 2.0)
    return (x, y, z)


def build_hair(mb):
    W = {"Head": 1.0}
    # «шапочка»: снизу (край) вверх к макушке; верх — купол с объёмом (волосы пышные, макушка 21 px = 1.650)
    levels = [None, (1.596, 0.0), (1.618, 0.37), (1.636, 0.67), (1.648, 0.87)]
    rings = []
    for lv in levels:
        ids = []
        for deg in HAIR_COLS:
            th = rad(deg)
            if lv is None:
                z = hairline_z(th); off = 0.007 if abs(deg) < 40 else 0.011
                x, y, _ = hair_pt(th, z, off)
            else:
                z, f = lv                               # f — доля купола: 0 — по форме головы, 1 — макушка
                x0, y0, _ = hair_pt(th, 1.596, 0.012)
                k = math.sqrt(max(1.0 - f * f, 0.0))
                x, y = x0 * k, HYC + 0.004 + (y0 - HYC - 0.004) * k
            ids.append(mb.vert(hx((x, y, z)), W))
        rings.append(ids)
    pole = mb.vert(hx((0, HYC + 0.004, 1.654)), W)
    loft(mb, rings, "hair_cap", "hair_cap", mat=1, pole=pole, seam=HAIR_COLS.index(180), inside=hx((0, HYC, 1.56)))
    # «занавес»: от висков вокруг затылка до плеч
    rows = []
    for z, off in CUR_ROWS:
        ids = []
        for deg in CUR_COLS:
            th = rad(deg)
            o = off * (1.0 if abs(deg) > 60 else 0.85)           # спереди у лица пряди прилегают ближе
            zz = z - (0.010 if abs(deg) > 150 and z < 1.45 else 0.0)
            ids.append(mb.vert(hx(hair_pt(th, zz, o)), W))
        rows.append(ids)
    loft(mb, rows, "hair_cur", "hair_cur", closed=False, mat=1, inside=hx((0, HYC, 1.52)))
    # отдельные пряди у лица (плоские «карточки» с альфой)
    cards = [  # (угол, z, вынос) ..., ширина
        ([(56, 1.592, 0.009), (59, 1.540, 0.014), (62, 1.480, 0.028), (64, 1.418, 0.048)], 0.024),
        ([(-56, 1.592, 0.009), (-59, 1.540, 0.014), (-62, 1.480, 0.028), (-64, 1.418, 0.048)], 0.024),
        ([(64, 1.590, 0.011), (66, 1.535, 0.018), (68, 1.472, 0.034), (70, 1.412, 0.056)], 0.030),
        ([(-64, 1.590, 0.011), (-66, 1.535, 0.018), (-68, 1.472, 0.034), (-70, 1.412, 0.056)], 0.030),
    ]
    for pts, width in cards:
        rws = []; v = 0.0; prev = None
        for k, (deg, z, off) in enumerate(pts):
            th = rad(deg)
            c = Vector(hair_pt(th, z, off)); tang = Vector((math.cos(th), math.sin(th), 0))
            hw = width / 2 * (1.0 if k < len(pts) - 1 else 0.6)
            if prev is not None:
                v += (c - prev).length
            prev = c
            rws.append((mb.vert(hx(c - tang * hw), W), mb.vert(hx(c + tang * hw), W), v))
        fis = []
        vs = 0.1 / rws[-1][2]
        for k in range(len(rws) - 1):
            a0, a1, va = rws[k]; b0, b1, vb = rws[k + 1]
            fis.append(mb.face((a0, b0, b1, a1), ((0, -va * vs), (0, -vb * vs), (0.03, -vb * vs), (0.03, -va * vs)),
                               "hair_strand", "hair_strand", 1))
        mb.orient(fis, inside=hx((0, HYC, 1.52)))


def build_clip(mb):
    """Заколка-«уточка» со стразами на правом виске (на рисунке — слева от лица)."""
    th = rad(-50); z0 = 1.574
    c = Vector(hair_pt(th, z0, 0.013))
    n = Vector((math.sin(th), -math.cos(th), 0)).normalized()        # наружу от головы
    t = Vector((math.cos(th), math.sin(th), 0))                      # по касательной (вбок-назад)
    up = Vector((0, 0, 1))
    ax = (up * math.cos(rad(28)) + t * math.sin(rad(28))).normalized()   # наклон, как на рисунке
    sd = ax.cross(n).normalized()
    L, Wd = 0.018, 0.0055
    q = [c - ax * L - sd * Wd, c + ax * L - sd * Wd, c + ax * L + sd * Wd, c - ax * L + sd * Wd]
    ids = [mb.vert(hx(p), {"Head": 1.0}) for p in q]
    fi = mb.face(ids, ((0, 0), (0.036, 0), (0.036, -0.011), (0, -0.011)), "clip", "clip", 1)
    mb.orient([fi], direction=n)


# --- капюшон, лежащий на спине; внутренний край — серый мех, он же меховой воротник спереди ---
HOOD_M = [  # угол вокруг шеи; профиль (радиус, z): внутренний край (мех), гребень, наружная часть, низ, кромка
    (30, [(0.060, 1.390), (0.074, 1.402), (0.092, 1.392), (0.100, 1.372), (0.096, 1.352)]),
    (60, [(0.066, 1.398), (0.092, 1.422), (0.122, 1.404), (0.134, 1.374), (0.132, 1.350)]),
    (90, [(0.070, 1.404), (0.104, 1.438), (0.138, 1.412), (0.150, 1.370), (0.146, 1.336)]),
    (125, [(0.072, 1.405), (0.112, 1.446), (0.148, 1.404), (0.154, 1.330), (0.144, 1.280)]),
    (155, [(0.072, 1.403), (0.116, 1.452), (0.150, 1.394), (0.152, 1.292), (0.140, 1.214)]),
    (180, [(0.072, 1.402), (0.118, 1.454), (0.150, 1.390), (0.150, 1.282), (0.136, 1.185)]),
]


def build_hood(mb):
    yc = 0.020
    stations = []
    seq = HOOD_M + [(-d, p) for d, p in reversed(HOOD_M[:-1])]
    for deg, prof in seq:
        th = rad(deg)
        stations.append(mb.ring([(r * math.sin(th), yc - r * math.cos(th), z) for r, z in prof], {"Spine": 1.0}))

    def tagfn(i, j0, j1):
        return "fur" if min(j0, j1) == 0 else "hood"

    loft(mb, stations, "hood", "hood", closed=False, tagfn=tagfn, inside=Vector((0, yc, 1.36)))
    ngon(mb, stations[0], "hood_cap", "fur", (-math.cos(rad(30)), -math.sin(rad(30)), 0))
    ngon(mb, stations[-1], "hood_cap", "fur", (math.cos(rad(30)), -math.sin(rad(30)), 0))


def build_all():
    mb = MB()
    T = build_torso(mb)
    setup_arm_globals()
    for sx in (1, -1):
        Y["build_arm"](mb, T, sx)
    build_jeans(mb)
    setup_boot_globals()
    for sx in (1, -1):
        Y["build_boot"](mb, sx)
    build_turtleneck(mb); build_head(mb); build_hair(mb); build_clip(mb); build_hood(mb)
    mb.fobj = [0] * len(mb.faces)
    return mb


# =====================================================================================
#  Сцена (без temp_override: окно переключается на нашу сцену, операторы — напрямую)
# =====================================================================================
def get_scene():
    sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    bpy.context.window.scene = sc
    sc.unit_settings.system = 'METRIC'
    return sc


def ensure_ctx(sc, obs=(), active=None):
    if bpy.context.window.scene is not sc:
        bpy.context.window.scene = sc
    ob = bpy.context.view_layer.objects.active
    if ob is not None and ob.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()
    for o in sc.objects:
        o.select_set(o in obs)
    bpy.context.view_layer.objects.active = active


def clear_own(sc):
    ensure_ctx(sc)
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.armatures, bpy.data.cameras):
        for d in list(blk):
            if d.users == 0 and (d.name.startswith(NAME) or d.name.startswith("MgPrev") or d.name.startswith("Yurchik")):
                blk.remove(d)
    for ac in list(bpy.data.actions):
        if ac.name.startswith(NAME + "_"):
            bpy.data.actions.remove(ac)


# =====================================================================================
#  Текстура
# =====================================================================================
def load_rgb(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    a = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)[::-1, :, :3].copy()


def prep_refs():
    turn = load_rgb(os.path.join(REF_DIR, "margo_turnaround.png"))
    bg = np.median(np.concatenate([turn[:, 0:20], turn[:, 470:520], turn[:, 820:880]], axis=1), axis=1)
    fg = np.abs(turn - bg[:, None, :]).max(axis=2) > 0.07
    fg = Y["erode"](fg, 2)                                          # без светлого ореола по контуру
    art = load_rgb(os.path.join(REF_DIR, "margo_face_art.png"))

    def patch(img, x0, x1, y0, y1):
        return np.median(img[y0:y1, x0:x1].reshape(-1, 3), axis=0)
    tones = {"skin": patch(art, 160, 180, 258, 272), "skin2": patch(art, 226, 246, 258, 272),
             "lips": patch(art, 196, 222, 314, 322), "jacket": patch(turn, 250, 270, 220, 260),
             "fur": patch(turn, 262, 272, 120, 135), "pink": None}
    tn = turn[140:280, 195:240].reshape(-1, 3)
    pk = tn[(tn[:, 0] - tn[:, 1] > 0.15)]
    tones["pink"] = np.median(pk, axis=0) if len(pk) > 20 else np.array((0.78, 0.36, 0.52), np.float32)
    dk = tn[(tn[:, 0] - tn[:, 1] < 0.05) & (tn.mean(axis=1) < 0.35)]
    tones["stripe_dark"] = np.median(dk, axis=0) if len(dk) > 20 else np.array((0.14, 0.12, 0.13), np.float32)
    return {"turn": Y["fill_invalid"](turn, fg, 40), "art": art, "tones": tones}


def sample(img, px, py):
    return Y["sample"](img, px, py)


def project_turn(refs, P, N, front=1.0, back=1.0, side=0.0):
    """Цвет с тёрнэраунда: смешиваем виды спереди / сзади / сбоку по нормали (P — метры тёрнэраунда)."""
    side = np.broadcast_to(np.asarray(side, np.float32), (len(P),))
    wf = np.clip(-N[:, 1], 0, 1) ** 2 * front + 0.02 * front
    wb = np.clip(N[:, 1], 0, 1) ** 2 * back + 0.02 * back
    ws = np.abs(N[:, 0]) ** 2 * side
    pz = T_GY - P[:, 2] / T_S
    img = refs["turn"]
    c = (sample(img, T_CXF + P[:, 0] / T_S, pz) * wf[:, None] + sample(img, T_CXB - P[:, 0] / T_S, pz) * wb[:, None]
         + sample(img, T_CXS - P[:, 1] / T_S, pz) * ws[:, None])
    return c / (wf + wb + ws + 1e-6)[:, None]


def paint_face(refs, P, N):
    t = refs["tones"]
    Q = unhx(P)
    x, z = Q[:, 0], Q[:, 2]
    ax = np.abs(x)
    # по X рисунок линейный до наружных уголков глаз (62 px), дальше растянут: край лица на рисунке (≈72 px,
    # дальше — волосы) ложится на край лица модели (0.056 м), а не на щёки
    ex = 62 * ART_K
    dx = np.where(ax < ex, ax / ART_K, 62 + (ax - ex) / (0.056 - ex) * 10.0)
    art = sample(refs["art"], ART_CX + np.sign(x) * dx, ART_EY + (EYE_Z - z) / ART_K)
    lum = art.mean(axis=1); rb = art[:, 0] - art[:, 2]
    hairness = nsmooth((rb - 0.11) / 0.06) * nsmooth((lum - 0.45) / 0.10)      # на рисунке поверх лица — волосы
    skin = (t["skin"] * 0.5 + t["skin2"] * 0.5)[None, :]
    c = mix(art, skin * (0.9 + 0.2 * lum[:, None]), hairness)
    c = mix(c, skin * (0.85 + 0.25 * lum[:, None]), 0.75 * nsmooth((ax - ex) / 0.012))   # растянутый край — к коже
    # лоб над бровями: на рисунке там пряди у висков — на модели их закрывает «шапочка» волос, на коже их не рисуем
    c = mix(c, skin * (0.92 + 0.10 * lum[:, None]), nsmooth((z - 1.553) / 0.005) * nsmooth((ax - 0.016) / 0.008))
    # рисунок — только на передней части лица; бока, уши и затылок — кожа с запечённой тенью
    frontness = nsmooth((-N[:, 1] - 0.35) / 0.35) * (1 - nsmooth((ax - 0.050) / 0.008))
    side = skin * (0.80 + 0.15 * np.clip(N[:, 2], 0, 1))[:, None]
    c = mix(side, c, frontness)
    # септум-кольцо (фото): тонкая серебряная дуга под кончиком носа
    rz = 1.4992; rr = 0.0036
    d = np.abs(np.hypot(x, (z - rz) * 1.15) - rr)
    ring = nsmooth((0.0011 - d) / 0.0006) * (z < rz + 0.0008) * nsmooth((-N[:, 1] - 0.2) / 0.2)
    c = mix(c, col((0.80, 0.80, 0.84)), ring)
    c = c * (1 - 0.10 * np.clip(1 + N[:, 1] * 1.3, 0, 1) ** 1.5)[:, None]   # к бокам лица темнее
    return np.clip(c, 0, 1)


def hair_color(Q, u, v, seed=31, dens=60.0):
    strands = vnoise(u * dens, v * 2.0, seed)
    fine = vnoise(u * dens * 2.3, v * 5.0, seed + 6)
    c = col((0.78, 0.77, 0.72))[None, :] * (0.72 + 0.30 * strands[:, None] + 0.16 * fine[:, None])   # пепельный платинум
    z = Q[:, 2]
    c = c * (0.70 + 0.30 * nsmooth((z - 1.40) / 0.15))[:, None]          # к плечам — в тени, холоднее
    c = mix(c, c * col((0.88, 0.90, 0.96)), nsmooth((1.50 - z) / 0.08))
    return c


def paint_hair(tag, P, N, u, v):
    Q = unhx(P)
    n = len(P); alpha = np.ones(n, np.float32)
    tri = lambda x: 1 - np.abs((x % 1.0) - 0.5) * 2
    if tag == "hair_cap":
        c = hair_color(Q, u, v, 31, 90.0)
        part = np.exp(-(Q[:, 0] / 0.0022) ** 2) * (Q[:, 1] < -0.02)                # прямой пробор
        c = c * (1 - 0.35 * part)[:, None]
        alpha = (v > 0.10 * tri(u * 46 + 0.3 * np.sin(u * 19.0)) ** 1.4).astype(np.float32)   # край — кончики прядей
    elif tag == "hair_cur":
        c = hair_color(Q, u, v, 37, 70.0)
        length = 0.78 + 0.22 * (0.6 * tri(u * 13 + 0.2 * np.sin(u * 37.0)) ** 0.8 + 0.4 * tri(u * 31 + 0.4))
        alpha = (v < length).astype(np.float32)
        c = c * (1 - 0.25 * np.clip((v - 0.6) / 0.4, 0, 1))[:, None]
    elif tag == "hair_strand":
        c = hair_color(Q, u, v, 41, 9.0)
        alpha = (np.abs(u - 0.5) * 2 < (0.95 - 0.75 * v ** 1.6)).astype(np.float32)
    else:  # clip — серебряная заколка со стразами и двумя чёрными крестиками (рисунок)
        e = np.maximum(np.abs(u - 0.5) * 2, np.abs(v - 0.5) * 2 * 0.55)
        alpha = ((np.abs(u - 0.5) * 2) ** 2 + ((np.abs(v - 0.5) * 2) ** 6) * 0.0 < 1.0).astype(np.float32)
        alpha = alpha * (((np.abs(u - 0.5) * 2) ** 4 + (np.abs(v - 0.5) * 2) ** 4) < 1.0)
        gem = 0.75 + 0.5 * (np.sin(u * 60) * np.sin(v * 22) > 0.3)
        c = col((0.70, 0.70, 0.74))[None, :] * gem[:, None]
        cross = np.zeros(n, bool)
        for cu in (0.38, 0.62):
            du = np.abs(u - cu); dv = np.abs(v - 0.5)
            cross |= ((du < 0.025) & (dv < 0.28)) | ((dv < 0.08) & (du < 0.07))
        c = np.where(cross[:, None], col((0.06, 0.06, 0.07)), c)
        c = np.where((e > 0.86)[:, None], col((0.35, 0.35, 0.38)), c)
    return np.clip(c, 0, 1), alpha


def paint_hand(refs, tag, P, N):
    t = refs["tones"]
    skin = (t["skin"] * 0.5 + t["skin2"] * 0.5)[None, :] * col((0.86, 0.78, 0.86))     # бледно-лиловые руки (тёрнэраунд)
    c = skin * (0.72 + 0.22 * fbm(P[:, 0] * 300, P[:, 2] * 300, 51))[:, None]
    c = c * (0.75 + 0.25 * nsmooth((np.abs(P[:, 0]) - 0.30) / 0.03))[:, None]           # у манжеты — тень рукава
    pn = np.array(Y["HAND_PN"], np.float32)
    sx = np.where(P[:, 0] > 0, 1.0, -1.0)
    palm = N[:, 0] * pn[0] * sx + N[:, 1] * pn[1] + N[:, 2] * pn[2]
    c = c * (0.85 + 0.15 * np.clip(-palm, 0, 1))[:, None] * toplight(N, 0.8)
    return c


def make_painter(refs):
    t = refs["tones"]

    def paint(tag, refs_, P, N, LUV):
        n = len(P); alpha = np.ones(n, np.float32)
        u, v = LUV[:, 0], LUV[:, 1]
        if tag == "jacket":
            c = project_turn(refs, P, N, side=0.35)
        elif tag == "sleeve":
            c = project_turn(refs, P, N, side=0.12)          # сбоку рукав на тёрнэраунде перекрыт мехом и кистью
        elif tag == "lining":
            c = project_turn(refs, P, N, back=0.0, side=0.3)
            c = mix(c, col(t["fur"]) * (0.7 + 0.6 * vnoise(P[:, 0] * 700, P[:, 2] * 700, 13))[:, None], 0.35)
        elif tag == "inner":
            c = project_turn(refs, P, N, back=0.0, side=0.05)
        elif tag == "hood":
            c = project_turn(refs, P, N, front=0.3, back=1.0, side=0.6)
        elif tag == "fur":
            c = col(t["fur"]) * (0.65 + 0.70 * vnoise(P[:, 0] * 800, P[:, 2] * 800, 17))[:, None] * toplight(N, 0.6)
        elif tag == "neck":
            Q = unhx(P)
            ph = (Q[:, 2] - 1.388) / 0.0205                                   # полоски водолазки ~2 см
            stripe = nsmooth((np.abs((ph % 1.0) - 0.5) - 0.20) / 0.06)
            c = mix(col(t["stripe_dark"])[None, :] * np.ones((n, 1)), col(t["pink"]) * 0.95, stripe)
            c = c * (0.80 + 0.30 * vnoise(u * 160, v * 40, 5))[:, None]
            c = c * (1 - 0.45 * np.clip((N[:, 1] - 0.1) * 2.0, 0, 1))[:, None]      # сзади — в тени волос
            c = c * (1 - 0.35 * np.clip(N[:, 2], 0, 1))[:, None]                     # под подбородком — тень
        elif tag == "face":
            c = paint_face(refs, P, N)
        elif tag.startswith("hair") or tag == "clip":
            c, alpha = paint_hair(tag, P, N, u, v)
        elif tag == "jeans":
            c = project_turn(refs, P, N, side=0.5)
            c = c * (0.55 + 0.45 * np.clip((0.86 - P[:, 2]) / 0.08, 0, 1))[:, None]           # тень под курткой
        elif tag == "boot":
            c = project_turn(refs, P, N, side=1.0)
        elif tag == "sole":
            c = project_turn(refs, P, N, side=1.0) * 0.9
            c = np.where((N[:, 2] < -0.5)[:, None], col((0.05, 0.05, 0.05)), c)
        elif tag in ("hand", "thumb"):
            c = paint_hand(refs, tag, P, N)
        else:
            c = np.tile(col((0.02, 0.02, 0.024)), (n, 1))
        return np.clip(c, 0, 1), alpha

    return paint


ISL_DENS_M = {"head": 3.6, "neck": 0.6, "hair_cap": 0.9, "hair_cur": 1.0, "hair_strand": 1.2, "clip": 2.5,
              "hood": 0.85, "hood_cap": 0.4, "torso": 1.0, "sleeve": 1.0, "hand": 1.3, "thumb": 1.3, "pelvis": 0.35,
              "legL": 0.85, "legR": 0.85, "boot": 1.1, "sole": 0.6, "sole_cap": 0.3, "dark": 0.3}


# =====================================================================================
#  Скелет, анимации, экспорт
# =====================================================================================
def retarget_safe(sc, arm, clips):
    sc.render.fps = R["FPS"]; sc.render.fps_base = 1.0
    dad = arm.animation_data or arm.animation_data_create()
    for tr in list(dad.nla_tracks):
        dad.nla_tracks.remove(tr)
    dad.action = None
    MAP, NO_ALIGN = R["MAP"], R["NO_ALIGN"]
    order = [b.name for b in arm.data.bones if b.name in MAP]
    dw = arm.matrix_world
    dst_rest = {n: (dw @ arm.data.bones[n].matrix_local) for n in MAP}
    stats = {}
    for key, path in E["SRCS"].items():
        cl = [c for c in clips if c[1] == key]
        if not cl:
            continue
        ensure_ctx(sc)
        before = {blk: set(getattr(bpy.data, blk)) for blk in ("objects", "meshes", "armatures", "materials", "images", "actions")}
        bpy.ops.import_scene.gltf(filepath=path)
        imported = [o for o in bpy.data.objects if o not in before["objects"]]
        src = [o for o in imported if o.type == 'ARMATURE'][0]
        src_actions = {a.name: a for a in bpy.data.actions if a not in before["actions"]}
        sad = src.animation_data or src.animation_data_create()
        for tr in list(sad.nla_tracks):
            sad.nla_tracks.remove(tr)
        sw = src.matrix_world
        src_rest = {n: (sw @ src.data.bones[n].matrix_local) for n in MAP.values()}

        def bdir(m):
            return (m.to_3x3() @ Vector((0, 1, 0))).normalized()

        q0 = {n: (Quaternion() if n in NO_ALIGN else
                  R["rot_between"](bdir(dst_rest[n]), bdir(src_rest[s]))) for n, s in MAP.items()}
        hip_scale = arm.data.bones["Pelvis"].head_local.z / src.data.bones["pelvis"].head_local.z
        for name, _, sname, reverse, *rest in cl:
            sac = src_actions.get(sname) or next(a for n, a in src_actions.items() if n.split(".")[0] == sname)
            stats[name] = R["bake_clip"](sc, src, arm, sac, name, reverse, q0, src_rest, dst_rest, hip_scale, order,
                                         rest[0] if rest else None)
            tr = dad.nla_tracks[-1]
            tr.strips[0].action.name = NAME + "_" + name
        for o in imported:
            bpy.data.objects.remove(o, do_unlink=True)
        for a in src_actions.values():
            bpy.data.actions.remove(a)
        for blk in ("meshes", "armatures", "materials", "images"):
            coll = getattr(bpy.data, blk)
            for d in list(coll):
                if d not in before[blk] and d.users == 0:
                    coll.remove(d)
    sc.frame_set(0)
    return stats


def foot_check(sc, arm):
    out = {}
    dad = arm.animation_data
    for tr in dad.nla_tracks:
        ac = tr.strips[0].action
        dad.action = ac
        f0, f1 = [int(x) for x in ac.frame_range]
        lo = 9.0
        for f in range(f0, f1 + 1, 2):
            sc.frame_set(f)
            for s in ("L", "R"):
                pb = arm.pose.bones["Foot" + s]
                lo = min(lo, (arm.matrix_world @ pb.tail).z, (arm.matrix_world @ pb.head).z)
        out[tr.name] = round(lo, 3)
    dad.action = None
    sc.frame_set(0)
    return out


def export_gltf(sc, arm, body):
    ensure_ctx(sc, [arm, body], arm)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(ROOT, "assets", "models", "margo.gltf"), use_selection=True, use_active_scene=True,
        export_format='GLTF_SEPARATE', export_keep_originals=True, export_apply=False, export_skins=True,
        export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
        export_frame_step=1, export_optimize_animation_size=True, export_anim_single_armature=True,
        export_def_bones=False, export_reset_pose_bones=True, export_bake_animation=False)


# =====================================================================================
#  Сравнение с Юрчиком и превью
# =====================================================================================
def add_yurchik(sc):
    path = os.path.join(ROOT, "assets", "models", "yurchik.gltf")
    ensure_ctx(sc)
    before = set(bpy.data.objects); before_ac = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for a in list(bpy.data.actions):
        if a not in before_ac:
            bpy.data.actions.remove(a)
    for o in new:
        if o.parent is None:
            o.location.x += 0.9
        if o.animation_data:
            o.animation_data.action = None
            for tr in list(o.animation_data.nla_tracks):
                o.animation_data.nla_tracks.remove(tr)
        if o.type == 'ARMATURE':
            for pb in o.pose.bones:
                pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0)
                pb.scale = (1, 1, 1)
        o.name = "YurchikRef_" + o.name
    return new


def preview(sc, tag):
    """Ортографические рендеры в масштабе тёрнэраунда (1 px = T_S м): их можно класть рядом с референсом."""
    if not PREVIEW:
        return []
    os.makedirs(PREVIEW, exist_ok=True)
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.color_type = 'TEXTURE' if STAGE != "geo" else 'MATERIAL'
    sc.display.shading.show_specular_highlight = False
    sc.display.shading.show_backface_culling = True
    sc.display.shading.studiolight_rotate_z = math.radians(-25)
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    if sc.world is None:
        sc.world = bpy.data.worlds.new("MgPrevWorld")
    cam_d = bpy.data.cameras.new("MgPrevCam"); cam_d.type = 'ORTHO'
    cam = bpy.data.objects.new("MgPrevCam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
    refs = [o for o in sc.objects if o.name.startswith("YurchikRef_")]
    outs = []
    H = int(T_GY - T_TOP + 40)
    shots = [("front", Vector((0, -1, 0)), (500, H), 0.0), ("side", Vector((-1, 0, 0)), (500, H), 0.0),
             ("back", Vector((0, 1, 0)), (500, H), 0.0),
             ("face", Vector((0, -1, 0.0)), (600, 600), 1.52), ("face34", Vector((0.6, -1, 0.05)), (600, 600), 1.52),
             ("faceside", Vector((1, -0.05, 0.0)), (600, 600), 1.52), ("q34", Vector((0.7, -1, 0.15)), (700, 1000), 0.0),
             ("withyur", Vector((0.15, -1, 0.05)), (900, 1000), 0.0)]
    for name, d, (rw, rh), zc in shots:
        d = d.normalized()
        for o in refs:
            o.hide_render = name != "withyur"
        sc.display.shading.light = 'STUDIO' if (STAGE == "geo" or name.startswith("face") or name == "q34") else 'FLAT'
        sc.render.resolution_x, sc.render.resolution_y = rw, rh
        if name.startswith("face"):
            cam_d.ortho_scale = 0.32; tgt = Vector((0, -0.01, zc))
        elif name in ("q34", "withyur"):
            cam_d.ortho_scale = 2.05 if name == "withyur" else 1.9
            tgt = Vector((0.45 if name == "withyur" else 0.0, 0, 0.90))
        else:
            cam_d.ortho_scale = max(rw, rh) * T_S
            tgt = Vector((0, 0, (rh / 2 - 20) * T_S))
        cam.location = tgt + d * 6
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(PREVIEW, "margo_%s_%s.png" % (tag, name))
        bpy.ops.render.render(write_still=True)
        outs.append(sc.render.filepath)
    bpy.data.objects.remove(cam, do_unlink=True)
    for o in refs:
        o.hide_render = False
    return outs


# =====================================================================================
def main():
    sc = get_scene()
    clear_own(sc)
    mb = build_all()
    Y["ISL_DENS"].update(ISL_DENS_M)
    D, pos = Y["pack_islands"](mb, size=ATLAS)
    mats = [Y["make_material"](NAME + "Mat", None, False), Y["make_material"](NAME + "Hair", None, True)]
    body, fsel, used = Y["make_object"](mb, 0, NAME + "Mesh", sc.collection, mats)
    tri = lambda pred: sum(len(mb.faces[f]) - 2 for f in fsel if pred(f))
    info = {"stage": STAGE, "height": round(max(p.z for p in mb.co), 3), "tris": tri(lambda f: True),
            "head_tris": tri(lambda f: mb.fisl[f] == "head"), "hair_tris": tri(lambda f: mb.fisl[f].startswith("hair")),
            "verts": len(used), "density_px_per_m": round(D, 1)}
    sys.path.insert(0, HERE); import ps2_budget
    info["budget"] = ps2_budget.check(NAME, info["tris"], "character")
    add_yurchik(sc)
    if STAGE in ("tex", "full"):
        refs = prep_refs()
        Y["paint"] = make_painter(refs)
        rgba, Tb = Y["bake_atlas"](mb, {0: (body.data, fsel)}, refs)
        import ps2_style
        importlib.reload(ps2_style)
        img = Y["save_atlas"](rgba, "margo")
        Y["make_material"](NAME + "Mat", img, False)
        Y["make_material"](NAME + "Hair", img, True)
        info["atlas_fill"] = round(float((Tb >= 0).mean()), 3)
        info["tones"] = {k: [round(float(c), 3) for c in v] for k, v in refs["tones"].items()}
    if STAGE == "full":
        Y["BONES"] = make_bones()
        ensure_ctx(sc)
        arm = E["rig"](body, used, mb, NAME)
        info["clips"] = retarget_safe(sc, arm, CLIPS)
        info["foot_min_z"] = foot_check(sc, arm)
        export_gltf(sc, arm, body)
        for pb in arm.pose.bones:
            pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
        ensure_ctx(sc)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "margo.blend"), copy=True)
    info["previews"] = preview(sc, STAGE)
    return info


result = main()
