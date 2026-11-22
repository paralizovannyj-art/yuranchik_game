# -*- coding: utf-8 -*-
# Сергей v2 (YUR-23): бессмертный преследователь. Рост ~2.2 м (≈1.25 Юрчика, как на картинке-сравнении).
#
# Референсы: docs/references/sergey/
#   sergey_turnaround.png      — ГЛАВНЫЙ: лицо, шапка, ворот, одежда спереди/сбоку/сзади (как концепт у Юрчика);
#   sergey_photo_main.png      — живое фото: по нему сверяли ауру и ухмылку (в текстуру больше не идёт);
#   sergey_vs_yurchik_scale.png — рост и массивность относительно Юрчика.
#
# Как устроено (пайплайн Юрчика, tools/blender/build_yurchik_v3.py, подключён через build_enemies.py):
#   * сетка строится «в пространстве Юрчика» (рост 1.78), затем вся модель масштабируется K = SERGEY_HEIGHT / 1.783;
#   * сечения парки, ног и капюшона сняты с тёрнэраунда (в единицах Юрчика), корпус — с запасом BULK («громаднее»);
#   * голова и шапка сняты с тёрнэраунда (профиль сбоку, ширины спереди, ориентиры — TURN_HEAD ниже),
#     голова плотнее, чем у Юрчика (≈1100 треугольников), черты лица — гладкие «бугры» по тем же ориентирам;
#   * текстура 512 (PS2: атлас персонажа ≤ 512, docs/design/ps2-style) — как у Юрчика: всё (лицо, шапка, ворот, одежда) — проекция тёрнэраунда спереди/сбоку/сзади
#     по нормали; голова — со своей привязкой видов (вид сбоку и сзади на тёрнэраунде нарисован на ~5 px ниже);
#     свет «запечён»;
#   * скелет — те же 15 костей, что у Юрчика и офников; анимации Quaternius UAL (CC0) — те же 15 клипов, что были.
#
# Запуск — ТОЛЬКО в открытом Blender (через Blender MCP или вкладку Scripting), без temp_override:
#   exec(open(r"C:\Users\mrs\Documents\yuranchik_game\tools\blender\build_sergey_v2.py", encoding="utf-8").read(),
#        {"YUR_ROOT": r"C:\Users\mrs\Documents\yuranchik_game", "YUR_STAGE": "geo"})
# YUR_STAGE: "geo" — сетка; "tex" — + текстура; "full" — + скелет, анимации, экспорт assets/models/sergey.gltf
# и копия сцены в tools/blender/sergey_v2.blend. YUR_PREVIEW = папка — сохранить превью-рендеры туда.
# Оси Blender: Z вверх, персонаж смотрит в -Y (в Godot это +Z), левая сторона персонажа — +X.
import bpy, os, math, json, importlib, sys
import numpy as np
from mathutils import Vector, Quaternion

ROOT = globals().get("YUR_ROOT", r"C:\Users\mrs\Documents\yuranchik_game")
STAGE = globals().get("YUR_STAGE", "full")
PREVIEW = globals().get("YUR_PREVIEW")
HERE = os.path.join(ROOT, "tools", "blender")
REF_DIR = os.path.join(ROOT, "docs", "references", "sergey")
SCENE = "SergeyV2"
NAME = "Sergey"
ATLAS = 512

SERGEY_HEIGHT = 2.20             # м, от подошвы до макушки шапки (≈1.25 Юрчика, как на sergey_vs_yurchik_scale.png)
UNIT_TOP = 1.783                 # макушка шапки в «пространстве Юрчика»
K = SERGEY_HEIGHT / UNIT_TOP     # общий масштаб модели
DX_ARM = 0.020                   # руки шире (плечи + корпус «громаднее»), в единицах Юрчика
DX_LEG = 0.012                   # ноги шире
HAND_SCALE = 1.12                # кисти крупнее

# --- тёрнэраунд: 1 px = T_S м (финальные метры), земля — строка T_GY, центры видов по X ---
T_S = SERGEY_HEIGHT / (689 - 30)
T_GY = 689.0
T_CXF, T_CXS, T_CXB = 240.5, 629.8, 1058.0
# --- голова на тёрнэраунде: свой центр вида спереди и сдвиг видов сбоку/сзади по вертикали (px) ---
# Ориентиры, снятые с картинки (px спереди -> единицы Юрчика: z = (689 - py) * T_S / K):
#   макушка шапки 30 -> 1.782, край шапки по центру 60 -> 1.702, брови 72.5 -> 1.668, глаза 78.7 -> 1.651
#   (x = 228 / 254 -> ±0.035), низ носа 93 -> 1.612, рот 104 -> 1.582, низ бородки 120 -> 1.540;
#   профиль (вид сбоку, px x -> y = -(px - T_CXS) * T_S / K): лоб 690 -> -0.163, кончик носа 692.5 -> -0.169,
#   под носом 685 -> -0.150, губы 683 -> -0.145, подбородок 680 -> -0.137, под челюстью 676 -> -0.125,
#   шапка сзади 613 -> +0.045. Ширина шапки ±0.092, лица на уровне рта ±0.064.
TH_CXF = 241.3
TH_DY_SIDE = 5.0
TH_DY_BACK = 5.0


def load(name, cut):
    src = open(os.path.join(HERE, name), encoding="utf-8").read()
    ns = {"YUR_ROOT": ROOT, "__file__": os.path.join(HERE, name)}
    exec(compile(src[:src.rindex(cut)], name, "exec"), ns)
    return ns


E = load("build_enemies.py", "\nmain()")              # заодно грузит Юрчика (Y) и перенос анимаций (R)
Y, R = E["Y"], E["R"]
MB, loft, ngon, dark_cap, sellipse, mx = Y["MB"], Y["loft"], Y["ngon"], Y["dark_cap"], Y["sellipse"], Y["mx"]
rad, clamp, lerp, smooth = Y["rad"], Y["clamp"], Y["lerp"], Y["smooth"]
col, fbm, vnoise = Y["col"], Y["fbm"], Y["vnoise"]
toplight, mix, nsmooth = E["toplight"], E["mix"], E["nsmooth"]
Y["ATLAS"] = ATLAS
Y["RLEG_OVR"] = {}
HYC = -0.064                    # центр головы по Y: лицо Сергея на тёрнэраунде на 1.6 см впереди, чем у Юрчика


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
            if d.users == 0 and (d.name.startswith(NAME) or d.name.startswith("SgPrev") or d.name.startswith("Yurchik")):
                blk.remove(d)
    for ac in list(bpy.data.actions):
        if ac.name.startswith(NAME + "_"):
            bpy.data.actions.remove(ac)


# =====================================================================================
#  Парка (корпус): кольца сняты с тёрнэраунда; колонки — как у Юрчика + планка на кнопках спереди
# =====================================================================================
ST_COLS = [("c0", 0), ("pL", 6), ("qL", 14), ("L28", 28), ("L45", 45), ("L67", 67.5), ("L90", 90), ("L112", 112.5),
           ("L137", 137), ("L160", 160), ("b", 180), ("R160", -160), ("R137", -137), ("R112", -112.5), ("R90", -90),
           ("R67", -67.5), ("R45", -45), ("R28", -28), ("qR", -14), ("pR", -6)]
ST_IDX = {c[0]: i for i, c in enumerate(ST_COLS)}
PLACKET = {"c0": 0.0075, "pL": 0.0070, "pR": 0.0070}      # планка выступает вперёд
# z, полуширина a, вперёд bf, назад bb, центр yc, «квадратность» n   (единицы Юрчика)
ST_RINGS = [
    (1.500, 0.100, 0.092, 0.100, -0.020, 2.0),   # 0 воротник-стойка
    (1.440, 0.218, 0.120, 0.132, -0.012, 2.3),   # 1 плечи
    (1.340, 0.226, 0.164, 0.150, -0.014, 2.6),   # 2 кокетка (шов поперёк груди)
    (1.230, 0.224, 0.174, 0.152, -0.016, 2.6),
    (1.125, 0.226, 0.182, 0.156, -0.020, 2.6),   # 4 подмышка
    (1.020, 0.232, 0.192, 0.158, -0.024, 2.6),   # 5 верх клапанов карманов
    (0.940, 0.236, 0.198, 0.160, -0.026, 2.6),
    (0.855, 0.240, 0.200, 0.160, -0.026, 2.6),
    (0.770, 0.242, 0.198, 0.158, -0.024, 2.6),   # 8 подол (середина бедра)
]


def torso_w_s(z, x=0.0):
    if z >= 0.90:
        return Y["torso_w"](z, x)
    wp = 0.8
    k = 0.62 * smooth((0.92 - z) / 0.16)              # полы идут за бёдрами — ноги не протыкают парку
    side = clamp(x / 0.08, -1, 1)
    return {"Spine": (1 - wp) * (1 - k), "Pelvis": wp * (1 - k), "ThighL": k * (0.5 + 0.5 * side),
            "ThighR": k * (0.5 - 0.5 * side)}


def ring_params(z):
    rs = ST_RINGS
    z = clamp(z, rs[-1][0], rs[1][0])
    for i in range(1, len(rs) - 1):
        if rs[i][0] >= z >= rs[i + 1][0]:
            t = (rs[i][0] - z) / (rs[i][0] - rs[i + 1][0])
            return [lerp(rs[i][k], rs[i + 1][k], t) for k in range(1, 6)]
    return list(rs[-1][1:6])


def front_y(x, z):
    """Поверхность парки спереди на высоте z (для карманов)."""
    a, bf, bb, yc, n = ring_params(z)
    k = (1 - clamp(abs(x) / a, 0, 0.999) ** n) ** (1 / n)
    return yc - bf * k


def build_parka(mb):
    rings = []
    for i, (z, a, bf, bb, yc, n) in enumerate(ST_RINGS):
        ids = []
        for name, deg in ST_COLS:
            th = rad(deg)
            x, y = sellipse(a, bf, bb, yc, th, n)
            zz = z
            if i == 8:
                zz = z - 0.012 * max(0.0, math.cos(th)) ** 1.2
            if i >= 1 and name in PLACKET:
                y -= PLACKET[name]
            if i == 2:                                    # кокетка — едва заметный рубчик
                x *= 1.012; y = yc + (y - yc) * 1.012
            ids.append(mb.vert((x, y, zz), torso_w_s(zz, x)))
        rings.append(ids)
    hole = {(ST_IDX[a], ST_IDX[b]) for a, b in (("L67", "L90"), ("L90", "L112"), ("R112", "R90"), ("R90", "R67"))}

    def skip(i, j0, j1):
        return i in (1, 2, 3) and (j0, j1) in hole

    def tagfn(i, j0, j1):
        return "placket" if ST_COLS[j0][0] in PLACKET and ST_COLS[j1][0] in PLACKET else "parka"

    loft(mb, rings, "torso", "parka", seam=ST_IDX["R90"], skip=skip, tagfn=tagfn, inside=Vector((0, -0.02, 1.15)))
    dark_cap(mb, rings[8], (0, -0.024, 0.78), 0.5, (0, 0, 0.04), (0, 0, -1))
    dark_cap(mb, rings[0], (0, -0.020, 1.49), 0.55, (0, 0, -0.012), (0, 0, 1))
    return rings


def build_flap_pockets(mb):
    """Накладные карманы с клапанами внизу парки — клапан выступает (виден в профиль)."""
    for sx in (1, -1):
        for isl, (z0, z1, out, drop) in (("pflap", (0.958, 1.018, 0.016, 0.006)), ("pbag", (0.800, 0.958, 0.007, 0.0))):
            xs = (0.082, 0.205)
            base, top = [], []
            for x, z in ((xs[0], z1), (xs[1], z1), (xs[1], z0), (xs[0], z0)):
                y = front_y(x, z) + 0.003
                w = torso_w_s(z, sx * x)
                base.append(mb.vert((sx * x, y, z), w))
                zt = z - drop if z == z0 else z - 0.002
                xt = x + (0.004 if x == xs[0] else -0.006)
                top.append(mb.vert((sx * xt, front_y(xt, zt) - out, zt), w))
            fis = loft(mb, [base, top], isl + ("L" if sx > 0 else "R"), "parka", inside=Vector((sx * 0.14, -0.02, 0.9)))
            ngon(mb, top, isl + ("L" if sx > 0 else "R"), "parka", (0, -1, 0))


# капюшон (снят, лежит на спине): угол вокруг шеи; профиль (радиус, z): внутренний край (флис), гребень, наружу, низ, кромка
HOOD_S = [
    (30, [(0.082, 1.492), (0.100, 1.522), (0.124, 1.500), (0.134, 1.472), (0.130, 1.452)]),
    (60, [(0.086, 1.500), (0.112, 1.540), (0.146, 1.512), (0.156, 1.478), (0.152, 1.456)]),
    (90, [(0.088, 1.505), (0.118, 1.555), (0.160, 1.522), (0.172, 1.482), (0.166, 1.455)]),
    (125, [(0.088, 1.505), (0.124, 1.580), (0.176, 1.540), (0.190, 1.470), (0.178, 1.430)]),
    (155, [(0.086, 1.502), (0.122, 1.602), (0.180, 1.556), (0.196, 1.462), (0.176, 1.405)]),
    (180, [(0.085, 1.500), (0.120, 1.610), (0.180, 1.560), (0.196, 1.458), (0.172, 1.395)]),
]


def build_hood_down(mb):
    yc = -0.030
    stations = []
    seq = HOOD_S + [(-d, p) for d, p in reversed(HOOD_S[:-1])]
    for deg, prof in seq:
        th = rad(deg)
        stations.append(mb.ring([(r * math.sin(th), yc - r * math.cos(th), z) for r, z in prof], {"Spine": 1.0}))

    def tagfn(i, j0, j1):
        return "lining" if min(j0, j1) == 0 else "hood"

    loft(mb, stations, "hood", "hood", closed=False, tagfn=tagfn, inside=Vector((0, yc, 1.45)))
    ngon(mb, stations[0], "hood_cap", "lining", (-math.cos(rad(30)), -math.sin(rad(30)), 0))
    ngon(mb, stations[-1], "hood_cap", "lining", (math.cos(rad(30)), -math.sin(rad(30)), 0))


def build_snood(mb):
    """Толстый серый вязаный снуд/ворот под подбородком."""
    spec = [  # z спереди, z сзади, a, bf, bb, yc, вес Head, «флис» — спереди не выступает за линию челюсти (профиль)
        (1.536, 1.636, 0.083, 0.072, 0.088, -0.050, 1.0, True),     # край флиса: за челюстью заходит под шапку
        (1.534, 1.607, 0.110, 0.075, 0.097, -0.050, 1.0, True),     # скругление верха валика
        (1.530, 1.585, 0.122, 0.078, 0.100, -0.050, 1.0, True),     # широкий мягкий валик вокруг лица (вид спереди ±0.12)
        (1.506, 1.552, 0.118, 0.082, 0.100, -0.046, 0.7, False),
        (1.482, 1.516, 0.110, 0.084, 0.100, -0.038, 0.3, False),
        (1.450, 1.450, 0.100, 0.084, 0.098, -0.026, 0.0, False),
    ]
    def make(rows, d):
        rings = []
        for zf, zb, a, bf, bb, yc, wh, fleece in rows:
            pts = []
            for j in range(18):
                th = rad(360 / 18 * j)
                x, y = sellipse(a - d, bf - d, bb - d, yc, th, 2.1)
                if fleece:                                      # флис: поднимается только позади линии челюсти (y > -0.065)
                    z = zf + (zb - zf) * smooth((y + 0.065) / 0.015)
                else:
                    z = zf + (zb - zf) * ((1 - math.cos(th)) / 2) ** 0.8
                pts.append((x, y, z))
            rings.append(mb.ring(pts, {"Head": wh, "Spine": 1 - wh}))
        return rings
    loft(mb, make(spec, 0.0), "neck", "neck", seam=9)
    # изнанка ворота (односторонние грани в Godot): верхний край флиса и внутренняя стенка до шеи
    inner = [(1.536, 1.636, 0.083, 0.072, 0.088, -0.050, 1.0, True), (1.500, 1.560, 0.074, 0.060, 0.076, -0.045, 0.8, False),
             (1.450, 1.470, 0.062, 0.052, 0.060, -0.040, 0.3, False)]
    fis = loft(mb, make(inner, 0.003), "snood_in", "snood_in", seam=9, inside=Vector((0, -0.05, 1.5)))
    for f in fis:                                       # нормали внутрь
        mb.faces[f] = tuple(reversed(mb.faces[f])); mb.fuv[f] = list(reversed(mb.fuv[f]))


def build_throat(mb):
    """Шея и тень внутри ворота: заполняет просвет между челюстью и флисом (сквозь ворот не видно фона)."""
    spec = [  # z, a, bf, bb, yc, вес Head — верх спрятан в голове спереди и под шапкой сзади
        (1.640, 0.078, 0.030, 0.072, -0.030, 1.0), (1.600, 0.072, 0.035, 0.068, -0.035, 1.0),
        (1.560, 0.056, 0.042, 0.060, -0.040, 1.0), (1.510, 0.050, 0.048, 0.054, -0.045, 0.6),
        (1.450, 0.048, 0.048, 0.052, -0.045, 0.0)]
    rings = []
    for z, a, bf, bb, yc, wh in spec:
        pts = []
        for j in range(10):
            th = rad(36 * j)
            x, y = sellipse(a, bf, bb, yc, th, 2.0)
            pts.append((x, y, z))
        rings.append(mb.ring(pts, {"Head": wh, "Spine": 1 - wh}))
    loft(mb, rings, "throat", "throat", seam=5)


# =====================================================================================
#  Голова: сечения сняты с тёрнэраунда (профиль сбоку + ширины спереди) + гладкие «бугры» черт лица
# =====================================================================================
# колонки (градусы): гуще спереди, где черты лица
HEAD_COLS = [0, 5, 10, 15, 21, 28, 36, 45, 56, 70, 90, 110, 135, 160, 180, -160, -135, -110, -90, -70, -56, -45, -36,
             -28, -21, -15, -10, -5]
# кольца: z спереди, z сзади, полуширина, глубина вперёд, назад (от HYC). Перед лица по центру = HYC - bf:
# лоб -0.159, переносица -0.151, под носом -0.146, рот -0.141, подбородок -0.133, под челюстью -0.119.
H_RINGS_S = [
    (1.745, 1.745, 0.060, 0.065, 0.070),     # 0  макушка (под шапкой)
    (1.715, 1.715, 0.072, 0.090, 0.088),     # 1
    (1.690, 1.690, 0.076, 0.095, 0.094),     # 2  лоб
    (1.668, 1.668, 0.076, 0.093, 0.094),     # 3  брови
    (1.651, 1.650, 0.075, 0.087, 0.092),     # 4  глаза
    (1.630, 1.628, 0.073, 0.084, 0.088),     # 5  скулы
    (1.612, 1.606, 0.071, 0.082, 0.083),     # 6  кончик носа
    (1.598, 1.592, 0.068, 0.082, 0.078),     # 7  под носом
    (1.581, 1.578, 0.064, 0.077, 0.070),     # 8  рот
    (1.565, 1.566, 0.055, 0.074, 0.064),     # 9  под губой
    (1.548, 1.558, 0.044, 0.069, 0.058),     # 10 подбородок с бородкой (челюсть сужается к подбородку)
    (1.537, 1.556, 0.032, 0.058, 0.054),     # 11 под челюстью
    (1.528, 1.552, 0.020, 0.040, 0.048),     # 12 низ подбородка — скруглён к шее
]
HEAD_T = [0, 1, 2, 2.5, 3, 3.5, 4, 4.33, 4.67, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10, 10.5, 11, 12]


def head_params(t):
    t = clamp(t, 0, len(H_RINGS_S) - 1)
    i = min(int(t), len(H_RINGS_S) - 2); f = t - i
    return [lerp(H_RINGS_S[i][k], H_RINGS_S[i + 1][k], f) for k in range(5)]


def g(x, s):
    return math.exp(-(x / s) ** 2)


def face_disp(x, z, th):
    """Смещение поверхности лица вперёд (fwd) и вверх (up), единицы Юрчика. Ориентиры — в начале файла."""
    ax = abs(x); front = max(0.0, math.cos(th)) ** 1.5
    fwd = 0.0; up = 0.0
    # лицо не плоское: боковые части лица (виски, щёки у ушей) уходят назад
    fwd -= 0.010 * smooth((ax - 0.032) / 0.040) * (1 - smooth((1.540 - z) / 0.02))
    # нос: переносица (+0.005 на уровне глаз) -> кончик (+0.023 на 1.612), крылья, тень под носом
    mask = smooth((1.668 - z) / 0.012) * (1 - smooth((1.604 - z) / 0.008))
    fwd += (0.005 + 0.018 * smooth((1.651 - z) / 0.039)) * mask * g(ax, 0.011)
    fwd += 0.008 * g(ax - 0.015, 0.007) * g(z - 1.607, 0.006)               # крылья носа
    fwd -= 0.003 * g(ax, 0.012) * g(z - 1.596, 0.004)
    # надбровья и глазницы (глаза глубже — тяжёлый взгляд)
    fwd += 0.003 * g(z - 1.668, 0.008) * (1 - smooth((ax - 0.050) / 0.014))
    fwd -= 0.006 * g(ax - 0.035, 0.014) * g(z - 1.651, 0.009)
    # скулы
    fwd += 0.008 * g(ax - 0.052, 0.013) * g(z - 1.632, 0.013)
    # носогубные складки
    fwd -= 0.003 * g(ax - 0.026 - (1.600 - z) * 0.35, 0.004) * g(z - 1.590, 0.014)
    # губы: верхняя/нижняя, щель рта; ухмылка — левый (у персонажа) уголок чуть выше
    lip = 1 - smooth((ax - 0.026) / 0.006)
    fwd += 0.004 * g(z - 1.587, 0.005) * lip + 0.004 * g(z - 1.575, 0.005) * lip
    fwd -= 0.0015 * g(z - 1.581, 0.0025) * lip
    fwd -= 0.002 * g(ax, 0.016) * g(z - 1.566, 0.004)                    # ямка под нижней губой
    if x > 0:
        up += 0.002 * g(ax - 0.026, 0.008) * g(z - 1.581, 0.008)
    # подбородок с бородкой, впалые щёки
    fwd += 0.004 * g(ax, 0.020) * g(z - 1.548, 0.009)
    fwd -= 0.005 * g(ax - 0.045, 0.012) * g(z - 1.592, 0.013)
    return fwd * front, up * front


def build_head_s(mb):
    rings = []
    for t in HEAD_T:
        zf, zb, a, bf, bb = head_params(t)
        pts = []
        for deg in HEAD_COLS:
            th = rad(deg)
            x, y = sellipse(a, bf, bb, HYC, th, 2.2 if math.cos(th) > 0 else 2.0)
            z = zf + (zb - zf) * (1 - math.cos(th)) / 2
            fwd, up = face_disp(x, z, th)
            pts.append((x, y - fwd, z + up))
        rings.append(mb.ring(pts, {"Head": 1.0}))

    def useg(j0, j1):                                  # затылок под шапкой и капюшоном — мало текселей
        back = lambda j: math.cos(rad(HEAD_COLS[j])) < -0.2
        return 0.35 if back(j0) and back(j1) else 1.0

    loft(mb, rings, "head", "face", seam=HEAD_COLS.index(180), useg=useg)


# =====================================================================================
#  Сборка
# =====================================================================================
def beanie_rim(th):
    """Нижний край шапки (тёрнэраунд): спереди по центру 1.702, у висков 1.663, перед ухом 1.639, над ухом 1.625,
    сзади 1.605 (спереди и сбоку — совпадает с линией края на виде сбоку)."""
    c = math.cos(th)
    return 1.625 + 0.077 * max(c, 0.0) ** 1.6 - 0.020 * max(-c, 0.0)


# шапка: нижние кольца — от края (dz), верхние — по абсолютной высоте; спереди/сзади — граница по Y (профиль сбоку):
# спереди 1.69 -> -0.163, 1.716 -> -0.158, 1.743 -> -0.144, 1.770 -> -0.114; сзади +0.043 до 1.74, 1.770 -> +0.027;
# макушка 1.784 над y = -0.033 (купол чуть откинут назад); ширина спереди ±0.0925, на 1.756 — ±0.081, на 1.77 — ±0.061
BEANIE_LO = [(0.000, 0.0850, -0.161, 0.042), (0.010, 0.0930, -0.163, 0.046), (0.030, 0.0930, -0.157, 0.046),
             (0.040, 0.0910, -0.151, 0.045)]
BEANIE_HI = [(1.758, 1.700, 0.0830, -0.135, 0.043), (1.772, 1.750, 0.0680, -0.108, 0.038),
             (1.781, 1.772, 0.0450, -0.070, 0.024)]
BEANIE_YC = -0.059


def build_beanie_s(mb):
    NC = 16
    rings = []

    def ring(zfn, a, yf, yb):
        pts = []
        for j in range(NC):
            th = rad(360 / NC * j)
            x, y = sellipse(a, BEANIE_YC - yf, yb - BEANIE_YC, BEANIE_YC, th, 2.15)
            pts.append((x, y, zfn(th)))
        rings.append(mb.ring(pts, {"Head": 1.0}))

    for dz, a, yf, yb in BEANIE_LO:
        ring(lambda th, dz=dz: beanie_rim(th) + dz, a, yf, yb)
    for zf, zb, a, yf, yb in BEANIE_HI:
        ring(lambda th, zf=zf, zb=zb: zf + (zb - zf) * (1 - math.cos(th)) / 2, a, yf, yb)
    pole = mb.vert((0, -0.030, 1.785), {"Head": 1.0})
    loft(mb, rings, "beanie", "beanie", seam=NC // 2, pole=pole)
    # изнанка шапки (тёмные волосы/тень): без неё в Godot (односторонние грани) сквозь бока шапки виден фон
    inner = []
    for k, (dz, a, yf, yb) in enumerate(BEANIE_LO[:3]):
        pts = []
        for j in range(NC):
            th = rad(360 / NC * j)
            x, y = sellipse(a - 0.004, BEANIE_YC - yf - 0.004, yb - BEANIE_YC - 0.004, BEANIE_YC, th, 2.15)
            pts.append((x, y, beanie_rim(th) + dz))
        inner.append(mb.ring(pts, {"Head": 1.0}))
    fis = loft(mb, inner, "beanie_in", "beanie_in", seam=NC // 2, inside=Vector((0, BEANIE_YC, 1.70)))
    for f in fis:                                       # нормали внутрь — видна только изнутри шапки
        mb.faces[f] = tuple(reversed(mb.faces[f])); mb.fuv[f] = list(reversed(mb.fuv[f]))


SLEEVE_S = [(t, h * 1.10, tb, hb * 1.10, rd * 1.12, yc) for t, h, tb, hb, rd, yc in Y["SLEEVE"]]
P_RINGS_S = [(0.845, 0.178, 0.112, 0.108), (0.765, 0.214, 0.116, 0.112), (0.695, 0.222, 0.112, 0.112)]
LEG_S = [  # z, центр x, центр y, радиус x, радиус y — прямые джинсы (с тёрнэраунда)
    (0.630, 0.118, -0.020, 0.100, 0.106), (0.585, 0.120, -0.019, 0.095, 0.102), (0.565, 0.121, -0.018, 0.093, 0.099),
    (0.500, 0.123, -0.012, 0.089, 0.095), (0.437, 0.125, 0.000, 0.087, 0.093), (0.415, 0.126, 0.006, 0.087, 0.093),
    (0.300, 0.130, 0.016, 0.086, 0.093), (0.190, 0.131, 0.018, 0.085, 0.095), (0.112, 0.131, 0.018, 0.085, 0.097),
]


def has_bone(w, prefix):
    return any(b.startswith(prefix) and v > 1e-4 for b, v in w.items())


def hand_xform(p, sx):
    """Кисть: увеличение вокруг запястья + сдвиг руки наружу. Обратное преобразование — hand_unxform."""
    c = mx(Y["HAND_W"], sx)
    return c + (p - c) * HAND_SCALE


def build_all_s():
    mb = MB()
    T = build_parka(mb)
    Y["T_COLS"] = [(n, d, 'j') for n, d in ST_COLS]; Y["T_IDX"] = ST_IDX
    Y["SLEEVE"] = SLEEVE_S
    for sx in (1, -1):
        n0 = len(mb.co)
        Y["build_arm"](mb, T, sx)
        for i in range(n0, len(mb.co)):
            p = mb.co[i]
            if has_bone(mb.w[i], "Hand"):
                p = hand_xform(p, sx)
            mb.co[i] = p + Vector((sx * DX_ARM, 0, 0))
    Y["P_RINGS"] = P_RINGS_S; Y["LEG"] = LEG_S
    Y["build_pants"](mb)
    for sx in (1, -1):
        n0 = len(mb.co)
        Y["build_boot"](mb, sx)
        for i in range(n0, len(mb.co)):
            mb.co[i] = mb.co[i] + Vector((sx * DX_LEG, 0, 0))
    build_head_s(mb); build_throat(mb); build_snood(mb); build_beanie_s(mb)
    build_hood_down(mb)
    build_flap_pockets(mb)
    E["drop_faces"](mb, lambda i: mb.ftag[i] == "band_tail" or mb.fisl[i].startswith("pocket"))
    mb.fmat = [0] * len(mb.faces)
    mb.fobj = [0] * len(mb.faces)
    for i, p in enumerate(mb.co):                      # в финальный размер
        mb.co[i] = p * K
    return mb


def make_bones_s():
    out = []
    for n, h, t, p in Y["BONES"]:
        h = Vector(h); t = Vector(t)
        for pre, dx in (("UpperArm", DX_ARM), ("Forearm", DX_ARM), ("Hand", DX_ARM),
                        ("Thigh", DX_LEG), ("Shin", DX_LEG), ("Foot", DX_LEG)):
            if n.startswith(pre):
                sx = 1 if n.endswith("L") else -1
                h = h + Vector((sx * dx, 0, 0)); t = t + Vector((sx * dx, 0, 0))
        out.append((n, tuple(h * K), tuple(t * K), p))
    return out


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
    turn = load_rgb(os.path.join(REF_DIR, "sergey_turnaround.png"))
    bg = np.median(turn[5:40, -40:-5].reshape(-1, 3), axis=0)
    fg = np.abs(turn - bg).max(axis=2) > 0.07
    fg = Y["erode"](fg, 3)                                          # без чернильной обводки контуров
    def patch(x0, x1, y0, y1):
        return np.median(turn[y0:y1, x0:x1].reshape(-1, 3), axis=0)
    # цвета, снятые с тёрнэраунда (px, вид спереди): щёки, шапка, серый флис ворота
    tones = {"skin": patch(224, 232, 86, 94), "skin2": patch(250, 258, 86, 94), "beanie": patch(228, 254, 36, 52),
             "snood": patch(198, 210, 95, 110)}
    fl = np.concatenate([turn[92:130, 190:215].reshape(-1, 3), turn[92:130, 268:293].reshape(-1, 3)])
    fl = fl[(fl[:, 2] - fl[:, 0] > 0.02) & (fl.mean(axis=1) > 0.25)]           # только серо-голубой флис
    if len(fl) > 20:
        tones["snood"] = np.median(fl, axis=0)
    return {"turn": Y["fill_invalid"](turn, fg, 30), "tones": tones}


def sample(img, px, py):
    return Y["sample"](img, px, py)


def project_turn(refs, P, N, front=1.0, back=1.0, side=0.0):
    """Цвет с тёрнэраунда (P — финальные метры): смешиваем виды спереди / сзади / сбоку по нормали."""
    side = np.broadcast_to(np.asarray(side, np.float32), (len(P),))
    wf = np.clip(-N[:, 1], 0, 1) ** 2 * front + 0.02 * front
    wb = np.clip(N[:, 1], 0, 1) ** 2 * back + 0.02 * back
    ws = np.abs(N[:, 0]) ** 2 * side
    pz = T_GY - P[:, 2] / T_S
    img = refs["turn"]
    c = (sample(img, T_CXF + P[:, 0] / T_S, pz) * wf[:, None] + sample(img, T_CXB - P[:, 0] / T_S, pz) * wb[:, None]
         + sample(img, T_CXS - P[:, 1] / T_S, pz) * ws[:, None])
    return c / (wf + wb + ws)[:, None]


def skinness(c):
    """0..1: насколько цвет похож на кожу лица с тёрнэраунда (тёплый и светлый)."""
    return nsmooth(((c[:, 0] - c[:, 2]) - 0.10) / 0.06) * nsmooth((c[:, 0] - 0.33) / 0.08)


def coolness(c):
    """0..1: холодный серо-голубой цвет (флис ворота), а не кожа, шапка или оливковая парка."""
    return 1 - nsmooth(((c[:, 0] - c[:, 2]) + 0.005) / 0.035)


def project_head(refs, P, N, front=1.0, back=1.0, side=1.0, no_skin=None, keep=None):
    """Как project_turn, но для головы: свой центр вида спереди (TH_CXF) и сдвиг видов сбоку/сзади вниз
    (на тёрнэраунде фигуры сбоку и сзади нарисованы на ~5 px ниже, чем спереди).
    no_skin = цвет: для шапки и ворота вид, где в этой точке кожа (лицо рядом), не берём; если все виды — кожа,
    остаётся этот запасной цвет. keep(c) -> 0..1 — своё правило, какие цвета с видов брать (вместо «не кожа»)."""
    side = np.broadcast_to(np.asarray(side, np.float32), (len(P),))
    wf = np.clip(-N[:, 1], 0, 1) ** 2 * front + 0.02 * front
    wb = np.clip(N[:, 1], 0, 1) ** 2 * back + 0.02 * back
    ws = np.abs(N[:, 0]) ** 2 * side
    pz = T_GY - P[:, 2] / T_S
    img = refs["turn"]
    cf = sample(img, TH_CXF + P[:, 0] / T_S, pz)
    cb = sample(img, T_CXB - P[:, 0] / T_S, pz + TH_DY_BACK)
    cs = sample(img, T_CXS - P[:, 1] / T_S, pz + TH_DY_SIDE)
    if no_skin is not None:
        ok = keep or (lambda c: 1 - 0.97 * skinness(c))
        wf = wf * ok(cf); wb = wb * ok(cb); ws = ws * ok(cs)
    acc = cf * wf[:, None] + cb * wb[:, None] + cs * ws[:, None]
    tot = wf + wb + ws
    if no_skin is not None:
        acc = acc + col(no_skin)[None, :] * 0.01
        tot = tot + 0.01
    return acc / (tot + 1e-6)[:, None]


def knit_rib(base, u, v, n, rib=True):
    c = col(base) * (0.80 + 0.30 * fbm(u * 40, v * 40, 3))[:, None]
    if rib:
        c = c * (0.80 + 0.26 * (np.sin(u * n * 2 * np.pi) * 0.5 + 0.5) ** 0.7)[:, None]
    return c


def paint_face_s(refs, P, N, LUV):
    """Лицо — как у Юрчика: проекция тёрнэраунда спереди и сбоку (затылок под шапкой — немного вида сзади)."""
    Pu = P / K
    x, z = Pu[:, 0], Pu[:, 2]
    ax = np.abs(x)
    c = project_head(refs, P, N, back=0.3)
    th = np.degrees(np.arctan2(ax, -(Pu[:, 1] - HYC)))
    hair = nsmooth((th - 95) / 14)
    # полоса под краем шапки: на висках и над ушами — тёмные волосы, надо лбом — тень от края
    tb = np.arctan2(ax, -(Pu[:, 1] - BEANIE_YC)); cb = np.cos(tb)
    rim = 1.625 + 0.077 * np.clip(cb, 0, 1) ** 1.6 - 0.020 * np.clip(-cb, 0, 1)
    under = nsmooth((z - (rim - 0.016)) / 0.010)
    side = nsmooth((np.degrees(tb) - 30) / 15)
    hair = np.maximum(hair, under * side)
    c = c * (1 - 0.35 * under * (1 - side))[:, None]
    c = mix(c, col((0.09, 0.075, 0.07)) * (0.7 + 0.6 * vnoise(x * 600, z * 600, 41))[:, None], hair)
    # «бессмертная» аура: чуть бледнее, глазницы чуть темнее — лицо остаётся тем же, что на тёрнэраунде
    c = mix(c, col((0.55, 0.55, 0.56)) * c.mean(axis=1, keepdims=True) / 0.45, 0.05)
    sock = np.exp(-((ax - 0.035) / 0.016) ** 2 - ((z - 1.651) / 0.009) ** 2)
    c = c * (1 - 0.05 * sock)[:, None]
    # лёгкий запечённый объём: к бокам лица темнее
    c = c * (1 - 0.06 * np.clip(1 + N[:, 1] * 1.25, 0, 1) ** 1.5)[:, None]
    return np.clip(c, 0, 1) ** 0.92                                  # средние тона чуть светлее — как на тёрнэраунде


def make_painter_s(refs):
    t = refs["tones"]

    def paint(tag, refs_, P, N, LUV):
        n = len(P); alpha = np.ones(n, np.float32)
        u, v = LUV[:, 0], LUV[:, 1]
        Pu = P / K
        if tag in ("parka", "placket", "sleeve"):
            c = project_turn(refs, P, N, side=0.25)
            c = c * (0.80 + 0.20 * nsmooth((Pu[:, 2] - 0.78) / 0.25))[:, None]                    # подол темнее, мокрый
            wet = np.clip((0.86 - Pu[:, 2]) / 0.08, 0, 1) * fbm(Pu[:, 0] * 50, Pu[:, 2] * 90, 61)
            c = mix(c, c * 0.62, wet * 0.6)
        elif tag == "hood":
            c = project_turn(refs, P, N, front=0.25, back=1.0, side=0.6)
        elif tag == "lining":
            c = knit_rib(t["snood"] * 0.95, Pu[:, 0] * 8 + Pu[:, 1] * 8, Pu[:, 2] * 8, 0, rib=False)
            c = c * (0.70 + 0.55 * vnoise(Pu[:, 0] * 900, Pu[:, 2] * 900, 13))[:, None] * toplight(N, 0.6)
        elif tag == "neck":
            side = 1 - nsmooth((-0.075 - Pu[:, 1]) / 0.03)                                 # под подбородком — без вида сбоку
            c = project_head(refs, P, N, back=1.0, side=side, no_skin=t["snood"],          # серый флис ворота — с тёрнэраунда
                             keep=lambda c: 0.03 + 0.97 * coolness(c))
            c = mix(c * 1.15, col(t["snood"]) * 1.05, 0.30)                                # мягкий светлый флис, как на тёрнэраунде
            c = c * (1 - 0.50 * np.clip(N[:, 2], 0, 1))[:, None]                          # верх ворота под челюстью — в тени
            under = (nsmooth((-0.085 - Pu[:, 1]) / 0.03) * (1 - nsmooth((np.abs(Pu[:, 0]) - 0.03) / 0.05))
                     * nsmooth((Pu[:, 2] - 1.505) / 0.02))
            c = c * (1 - 0.50 * under)[:, None]                                           # спереди под подбородком — тень шеи
        elif tag == "beanie":
            c = project_head(refs, P, N, back=1.0, no_skin=t["beanie"])                    # шапка — с тёрнэраунда, как у Юрчика
        elif tag == "face":
            c = paint_face_s(refs, P, N, LUV)
        elif tag in ("throat", "snood_in"):                                                              # глубина ворота — с тёрнэраунда, в тени
            c = project_head(refs, P, N, back=1.0, side=0.3, no_skin=t["snood"], keep=lambda c: 0.03 + 0.97 * coolness(c))
            c = mix(c, col(t["snood"]), 0.25) * 0.62
        elif tag == "beanie_in":
            c = col((0.055, 0.045, 0.040)) * (0.8 + 0.4 * vnoise(Pu[:, 0] * 300, Pu[:, 2] * 300, 9))[:, None]
        elif tag in ("pants", "boot"):
            c = project_turn(refs, P, N, side=1.0 if tag == "boot" else 0.4)
            if tag == "pants":
                c = c * (0.50 + 0.50 * np.clip((0.80 - Pu[:, 2]) / 0.09, 0, 1))[:, None]          # тень под паркой
        elif tag == "sole":
            c = col((0.10, 0.10, 0.10)) * (0.7 + 0.6 * fbm(Pu[:, 0] * 90, Pu[:, 1] * 90, 5))[:, None]
            c = np.where((np.abs(N[:, 2]) < 0.5)[:, None], c * 2.4, c)                             # светлый рант
        elif tag in ("hand", "thumb"):
            sx = np.where(Pu[:, 0] > 0, 1.0, -1.0)
            hw = np.array(Y["HAND_W"], np.float32)
            c0 = np.stack([sx * hw[0], np.full(n, hw[1]), np.full(n, hw[2])], 1)
            q = Pu - np.stack([sx * DX_ARM, np.zeros(n), np.zeros(n)], 1)
            q = c0 + (q - c0) / HAND_SCALE
            q[:, 0] = np.abs(q[:, 0])                     # кисть рисуется по левой — правая её зеркало
            Nq = N.copy(); Nq[:, 0] = Nq[:, 0] * sx
            base = Y["paint_hand"](tag, q, Nq, v)
            lum = base.mean(axis=1, keepdims=True)
            glove = base[:, 1] < 0.21                     # у Юрчика перчатка тёмная, кожа светлее
            sk = (t["skin"] * 0.5 + t["skin2"] * 0.5)[None, :] * (0.40 + 1.0 * np.clip(lum, 0, 0.5))
            gl = col((0.030, 0.030, 0.034)) * (0.6 + 4.0 * lum)
            c = np.where(glove[:, None], gl, sk)
        else:
            c = np.tile(col((0.02, 0.02, 0.024)), (n, 1))
        return np.clip(c, 0, 1), alpha

    return paint


ISL_DENS_S = {"throat": 0.3, "snood_in": 0.3, "beanie_in": 0.2, "head": 3.6, "neck": 0.9, "beanie": 1.0, "hand": 1.3, "thumb": 1.3, "pelvis": 0.35, "sole": 0.5,
              "sole_cap": 0.3, "hood": 0.85, "hood_cap": 0.5, "boot": 1.0, "dark": 0.4, "pflapL": 1.0, "pflapR": 1.0,
              "pbagL": 0.8, "pbagR": 0.8}


# =====================================================================================
#  Скелет, анимации (без глобальной чистки чужих данных), экспорт
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
        for blk in ("meshes", "armatures", "materials", "images"):     # только то, что принёс импорт
            coll = getattr(bpy.data, blk)
            for d in list(coll):
                if d not in before[blk] and d.users == 0:
                    coll.remove(d)
    sc.frame_set(0)
    return stats


def foot_check(sc, arm):
    """Минимальная высота стоп по кадрам каждого клипа — стопы не должны висеть в воздухе или уходить в пол."""
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
        filepath=os.path.join(ROOT, "assets", "models", "sergey.gltf"), use_selection=True, use_active_scene=True,
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
            o.location.x += 1.25
        if o.animation_data:
            o.animation_data.action = None
            for tr in list(o.animation_data.nla_tracks):
                o.animation_data.nla_tracks.remove(tr)
        if o.type == 'ARMATURE':                          # поза покоя (A-поза), а не последний кадр анимации
            for pb in o.pose.bones:
                pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0)
                pb.scale = (1, 1, 1)
        o.name = "YurchikRef_" + o.name
    return new


def preview(sc, tag, height=SERGEY_HEIGHT):
    if not PREVIEW:
        return []
    os.makedirs(PREVIEW, exist_ok=True)
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'FLAT' if STAGE != "geo" else 'STUDIO'
    sc.display.shading.color_type = 'TEXTURE' if STAGE != "geo" else 'MATERIAL'
    sc.display.shading.show_specular_highlight = False      # без пластикового блеска — как в игре
    sc.display.shading.show_backface_culling = True          # изнанки не видно — как в игре
    sc.display.shading.studiolight_rotate_z = math.radians(-25)
    sc.render.resolution_x, sc.render.resolution_y = 1000, 1000
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    if sc.world is None:
        sc.world = bpy.data.worlds.new("SgPrevWorld")
    cam_d = bpy.data.cameras.new("SgPrevCam"); cam_d.type = 'ORTHO'
    cam = bpy.data.objects.new("SgPrevCam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
    outs = []
    refs = [o for o in sc.objects if o.name.startswith("YurchikRef_") and o.parent is None]
    shots = [("front", Vector((0, -1, 0.0)), Vector((0.62, 0, height * 0.5)), height * 1.08),
             ("side", Vector((1, 0, 0.0)), Vector((0, 0.62, height * 0.5)), height * 1.08),
             ("back", Vector((0, 1, 0.0)), Vector((0.62, 0, height * 0.5)), height * 1.08),
             ("face", Vector((0, -1, 0.04)), Vector((0, 0, 2.00)), 0.42),
             ("face34", Vector((0.55, -1, 0.04)), Vector((0, 0, 2.00)), 0.46),
             ("faceside", Vector((1, -0.08, 0.02)), Vector((0, 0, 2.00)), 0.46)]
    for name, d, tgt, scale in shots:
        d = d.normalized()
        # крупные планы лица — со светом, чтобы был виден объём; общие — плоско, как текстура
        sc.display.shading.light = 'STUDIO' if (STAGE == "geo" or name.startswith("face")) else 'FLAT'
        for o in refs:                                   # Юрчик рядом: сбоку — позади по Y, иначе — справа по X
            o.location = (0, 1.25, 0) if name == "side" else (1.25, 0, 0)
        cam_d.ortho_scale = scale
        cam.location = tgt + d * 6
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(PREVIEW, "sergey_%s_%s.png" % (tag, name))
        bpy.ops.render.render(write_still=True)
        outs.append(sc.render.filepath)
    bpy.data.objects.remove(cam, do_unlink=True)
    return outs


# =====================================================================================
def main():
    sc = get_scene()
    clear_own(sc)
    mb = build_all_s()
    Y["ISL_DENS"].update(ISL_DENS_S)
    D, pos = Y["pack_islands"](mb, size=ATLAS)
    mat = Y["make_material"](NAME + "Mat", None, False)
    body, fsel, used = Y["make_object"](mb, 0, NAME + "Mesh", sc.collection, [mat])
    info = {"stage": STAGE, "height": round(max(p.z for p in mb.co), 3), "tris": sum(len(mb.faces[f]) - 2 for f in fsel),
            "head_tris": sum(len(mb.faces[f]) - 2 for f in fsel if mb.fisl[f] == "head"), "verts": len(used),
            "density_px_per_m": round(D, 1)}
    add_yurchik(sc)
    if STAGE in ("tex", "full"):
        refs = prep_refs()
        Y["paint"] = make_painter_s(refs)
        rgba, _ = Y["bake_atlas"](mb, {0: (body.data, fsel)}, refs)
        sys.path.insert(0, HERE)
        import ps2_style
        importlib.reload(ps2_style)
        img = Y["save_atlas"](rgba, "sergey")
        Y["make_material"](NAME + "Mat", img, False)
        info["tones"] = {k: [round(float(c), 3) for c in v] for k, v in refs["tones"].items()}
    if STAGE == "full":
        Y["BONES"] = make_bones_s()
        ensure_ctx(sc)
        arm = E["rig"](body, used, mb, NAME)
        info["clips"] = retarget_safe(sc, arm, E["CLIPS"])
        info["foot_min_z"] = foot_check(sc, arm)
        export_gltf(sc, arm, body)
        for pb in arm.pose.bones:                         # превью — в позе покоя
            pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
        ensure_ctx(sc)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "sergey_v2.blend"), copy=True)
    info["previews"] = preview(sc, STAGE)
    return info


result = main()
