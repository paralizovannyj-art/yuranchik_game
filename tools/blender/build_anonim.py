# -*- coding: utf-8 -*-
# «Аноним»: low-poly NPC в стиле PS2 по тёрнэраунду docs/references/anonim/anonim_turnaround.webp
# (виды спереди / сбоку / сзади; anonim_photo.webp — то же худи на живом фото).
#
# Как устроено (пайплайн Марго / Юрчика / Сергея: build_margo.py, build_yurchik_v3.py, build_sergey_v2.py):
#   * сечения сняты с тёрнэраунда в пикселях и переведены в метры: 1 px = T_S м, земля — строка T_GY,
#     центры видов спереди / сбоку / сзади — T_CXF / T_CXS / T_CXB (сбоку он смотрит вправо);
#   * одежда: графитовое худи оверсайз с карманом-кенгуру и надетым глубоким капюшоном, прямые потёртые джинсы,
#     грубые трекинговые ботинки, чёрные перчатки без пальцев;
#   * ДВА ОТЛИЧИЯ от референса:
#       1) лица нет — под капюшоном «провал»: отдельная геометрия с отдельным материалом AnonimVoid
#          (в Godot — unshaded, #000000, без тумана), закрывает проём капюшона целиком и уходит внутрь чашей;
#       2) руки всегда в кармане-кенгуру — сетка смоделирована сразу в этой позе (локти согнуты и отведены назад,
#          предплечья уходят в боковые входы кармана), карман оттопырен кистями; кистей нет, у входа — край перчатки;
#   * текстура 512 (атлас персонажа PS2): одежда — проекция тёрнэраунда по нормали, свет «запечён»;
#   * скелет — те же 15 костей, что у Сергея, офников и Марго (свои положения суставов), анимации Quaternius UAL
#     (CC0); треки рук в анимациях заменяются позой покоя — руки не вылетают из кармана.
#
# Запуск — ТОЛЬКО в открытом Blender (через Blender MCP или вкладку Scripting), без temp_override:
#   exec(open(r"C:\Users\mrs\Documents\yuranchik_game\tools\blender\build_anonim.py", encoding="utf-8").read(),
#        {"YUR_ROOT": r"C:\Users\mrs\Documents\yuranchik_game", "YUR_STAGE": "geo"})
# YUR_STAGE: "geo" — сетка; "tex" — + текстура; "full" — + скелет, анимации, экспорт assets/models/anonim.gltf
# и копия сцены в tools/blender/anonim.blend. YUR_PREVIEW = папка — сохранить превью-рендеры туда.
# Оси Blender: Z вверх, персонаж смотрит в -Y (в Godot это +Z), левая сторона персонажа — +X.
import bpy, os, math, importlib, sys
import numpy as np
from mathutils import Vector, Quaternion

ROOT = globals().get("YUR_ROOT", r"C:\Users\mrs\Documents\yuranchik_game")
STAGE = globals().get("YUR_STAGE", "full")
PREVIEW = globals().get("YUR_PREVIEW")
HERE = os.path.join(ROOT, "tools", "blender")
REF_DIR = os.path.join(ROOT, "docs", "references", "anonim")
REF_TURN = os.path.join(REF_DIR, "anonim_turnaround.webp")
SCENE = "Anonim"
NAME = "Anonim"
ATLAS = 512

# --- тёрнэраунд (1376×768): 1 px = T_S м, земля — строка T_GY, макушка капюшона — T_TOP; центры видов по X ---
T_HEIGHT = 1.80                                  # до макушки капюшона (сам он ~1.76)
T_GY, T_TOP = 746.0, 42.0
T_S = T_HEIGHT / (T_GY - T_TOP)
T_CXF, T_CXS, T_CXB = 261.5, 694.0, 1145.5


def load(name, cut):
    src = open(os.path.join(HERE, name), encoding="utf-8").read()
    ns = {"YUR_ROOT": ROOT, "__file__": os.path.join(HERE, name)}
    exec(compile(src[:src.rindex(cut)], name, "exec"), ns)
    return ns


E = load("build_enemies.py", "\nmain()")              # грузит Юрчика (Y, строители и запекание) и перенос анимаций (R)
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

# =====================================================================================
#  Скелет: суставы Анонима (метры). Руки — сразу в позе «в кармане».
# =====================================================================================
JS = Vector((0.200, 0.010, 1.400))               # плечевой сустав (левый)
EL = Vector((0.258, 0.062, 1.130))               # локоть: согнут, отведён назад и чуть наружу
WR = Vector((0.158, -0.138, 1.026))              # запястье — у бокового входа кармана
HT = Vector((0.070, -0.168, 1.000))              # кончики пальцев в кармане (кисти не моделируются)


def make_bones():
    b = [("Pelvis", (0, -0.005, 0.900), (0, -0.005, 1.000), None),
         ("Spine", (0, -0.005, 1.000), (0, -0.012, 1.440), "Pelvis"),
         ("Head", (0, -0.014, 1.462), (0, -0.036, 1.700), "Spine")]
    for s, sx in (("L", 1), ("R", -1)):
        b += [("UpperArm" + s, tuple(mx(JS, sx)), tuple(mx(EL, sx)), "Spine"),
              ("Forearm" + s, tuple(mx(EL, sx)), tuple(mx(WR, sx)), "UpperArm" + s),
              ("Hand" + s, tuple(mx(WR, sx)), tuple(mx(HT, sx)), "Forearm" + s),
              ("Thigh" + s, (0.105 * sx, -0.005, 0.860), (0.124 * sx, 0.017, 0.478), "Pelvis"),
              ("Shin" + s, (0.124 * sx, 0.017, 0.478), (0.133 * sx, 0.040, 0.105), "Thigh" + s),
              ("Foot" + s, (0.133 * sx, 0.040, 0.105), (0.168 * sx, -0.125, 0.035), "Shin" + s)]
    return b


# =====================================================================================
#  Торс худи: 18 колонок (те же колонки продолжаются в капюшон), пройма — в колонках 70/90/110
# =====================================================================================
SIDE_D = [34, 52, 70, 90, 110, 135, 158]
COLS = [0, 18] + SIDE_D + [180] + [-d for d in reversed(SIDE_D)] + [-18]
CI = {d: i for i, d in enumerate(COLS)}
NC = len(COLS)
# z, полуширина a, вперёд bf, назад bb, центр yc, «квадратность» n. Спереди: худи ±80..86 px, резинка ±80;
# сбоку (центр 694 px): спина ~630 px, живот с карманом до 764 px — оверсайз висит мешком.
T_RINGS = [
    (0.846, 0.199, 0.150, 0.140, -0.005, 2.6),   # 0 низ резинки (резинка собирает ткань)
    (0.905, 0.207, 0.168, 0.158, -0.005, 2.6),   # 1 верх резинки
    (0.955, 0.213, 0.170, 0.164, -0.005, 2.6),   # 2 низ кармана
    (1.030, 0.216, 0.166, 0.165, -0.005, 2.6),   # 3
    (1.110, 0.213, 0.156, 0.165, -0.005, 2.6),   # 4 верх кармана
    (1.180, 0.208, 0.145, 0.165, -0.005, 2.6),   # 5
    (1.255, 0.204, 0.134, 0.163, -0.005, 2.5),   # 6 подмышка
    (1.320, 0.205, 0.123, 0.158, -0.005, 2.5),   # 7
    (1.388, 0.207, 0.112, 0.148, -0.006, 2.4),   # 8
    (1.450, 0.200, 0.100, 0.134, -0.007, 2.3),   # 9 верх проймы (плечо)
    (1.458, 0.150, 0.088, 0.120, -0.008, 2.2),   # 10 ворот = низ капюшона (по бокам выше, см. COLLAR_LIFT)
]
COLLAR_LIFT = 0.030                               # капюшон лежит на плечах: ворот по бокам и сзади выше, чем спереди
ARM_RINGS = (6, 9)                                # пройма: кольца 6..9
ARM_COLS = (70, 90, 110)


def torso_w(z):
    """Худи висит с плеч: выше резинки — целиком Spine (карман и рукава двигаются вместе, ничего не протыкает)."""
    k = 0.5 * smooth((0.935 - z) / 0.09)
    return {"Spine": 1 - k, "Pelvis": k}


def torso_params(z):
    rs = T_RINGS
    if z <= rs[0][0]:
        return rs[0][1:]
    for i in range(len(rs) - 1):
        if rs[i][0] <= z <= rs[i + 1][0]:
            t = (z - rs[i][0]) / (rs[i + 1][0] - rs[i][0])
            return tuple(lerp(rs[i][j], rs[i + 1][j], t) for j in range(1, 6))
    return rs[-1][1:]


def torso_front_y(x, z):
    a, bf, bb, yc, n = torso_params(z)
    q = min(abs(x) / a, 0.999)
    return yc - bf * (1 - q ** n) ** (1 / n)


def build_torso(mb):
    rings = []
    for i, (z, a, bf, bb, yc, n) in enumerate(T_RINGS):
        ids = []
        for deg in COLS:
            x, y = sellipse(a, bf, bb, yc, rad(deg), n)
            zz = z
            if i == 0:
                zz = z - 0.006 * max(0.0, math.cos(rad(deg)))
            if i == len(T_RINGS) - 1:
                zz = z + COLLAR_LIFT * smooth(abs(deg) / 70.0)
            ids.append(mb.vert((x, y, zz), torso_w(zz)))
        rings.append(ids)
    hole = set()
    for sx in (1, -1):
        for a_, b_ in zip(ARM_COLS[:-1], ARM_COLS[1:]):
            hole.add((CI[sx * a_], CI[sx * b_])); hole.add((CI[sx * b_], CI[sx * a_]))

    def skip(i, j0, j1):
        return ARM_RINGS[0] <= i < ARM_RINGS[1] and (j0, j1) in hole

    def tagfn(i, j0, j1):
        return "rib" if i == 0 else "hoodie"

    loft(mb, rings, "torso", "hoodie", seam=CI[180], skip=skip, tagfn=tagfn, inside=Vector((0, 0, 1.15)))
    dark_cap(mb, rings[0], (0, -0.005, 0.85), 0.55, (0, 0, 0.04), (0, 0, -1))
    return rings


def armhole(T, sx):
    """Пройма: 10 вершин торса по кругу (кольца 6..9, колонки 70/90/110)."""
    r0, r3 = ARM_RINGS
    c = [CI[sx * d] for d in ARM_COLS]
    return ([T[r3][c[0]], T[r3][c[1]], T[r3][c[2]], T[r3 - 1][c[2]], T[r3 - 2][c[2]],
             T[r0][c[2]], T[r0][c[1]], T[r0][c[0]], T[r0 + 1][c[0]], T[r0 + 2][c[0]]])


# =====================================================================================
#  Рукава: от проймы вниз, локоть согнут, предплечье уходит в боковой вход кармана
# =====================================================================================
# центр кольца (левый рукав), полуоси (поперёк в плоскости руки / по глубине), вес: 0 — плечо, 1 — предплечье
SLEEVE = [
    ((0.230, 0.012, 1.376), 0.070, 0.070, 0.0),
    ((0.243, 0.030, 1.282), 0.068, 0.068, 0.0),
    ((0.254, 0.050, 1.198), 0.067, 0.066, 0.0),
    ((0.260, 0.064, 1.136), 0.066, 0.065, 0.5),   # локоть (складки собираются)
    ((0.247, 0.040, 1.096), 0.064, 0.063, 1.0),
    ((0.226, -0.010, 1.070), 0.063, 0.060, 1.0),
    ((0.204, -0.060, 1.051), 0.059, 0.057, 1.0),   # напуск над манжетой
    ((0.190, -0.086, 1.042), 0.047, 0.046, 1.0),   # верх резинки манжеты
    ((0.166, -0.124, 1.030), 0.045, 0.044, 1.0),   # край манжеты — у входа кармана
]
GLOVE = [((0.150, -0.146, 1.024), 0.036, 0.034), ((0.128, -0.160, 1.018), 0.033, 0.030)]   # край перчатки в кармане
SL_N = 10


def path_frames(cs):
    """Касательные и устойчивые оси сечений вдоль ломаной центров."""
    out = []
    for k in range(len(cs)):
        a = cs[max(k - 1, 0)]; b = cs[min(k + 1, len(cs) - 1)]
        t = (b - a).normalized()
        ref = Vector((1, 0, 0))
        e1 = (ref - t * ref.dot(t)).normalized()
        e2 = t.cross(e1).normalized()
        out.append((t, e1, e2))
    return out


def match_ring(mb, ring0, pts):
    """Порядок вершин проймы, лучше всего совпадающий с первым кольцом рукава (сдвиг и направление)."""
    n = len(ring0); best = None
    for d in (1, -1):
        for s in range(n):
            cand = [ring0[(s + d * j) % n] for j in range(n)]
            e = sum((mb.co[c] - p).length for c, p in zip(cand, pts))
            if best is None or e < best[0]:
                best = (e, cand)
    return best[1]


def build_arm(mb, T, sx):
    s = "L" if sx > 0 else "R"
    UA, FA, HD = "UpperArm" + s, "Forearm" + s, "Hand" + s
    cs = [Vector(c) for c, *_ in SLEEVE] + [Vector(c) for c, *_ in GLOVE]
    fr = path_frames(cs)
    rings, allpts = [], []
    for k, (c, r1, r2, wf) in enumerate(SLEEVE):
        t, e1, e2 = fr[k]
        if k == 0:                       # верх рукава наклонён, как шов спущенного плеча: плечо плавно спадает к руке
            t = Vector((0.55, 0.0, -0.83)).normalized()
            e1 = (Vector((1, 0, 0)) - t * t.x).normalized(); e2 = t.cross(e1).normalized()
        pts, ws = [], []
        for j in range(SL_N):
            ph = rad(360.0 / SL_N * j)
            fold = 1.0 + (0.05 * math.sin(3 * ph + k * 1.7) if 2 <= k <= 6 else 0.0)   # мятые складки
            p = Vector(c) + e1 * (r1 * math.cos(ph) * fold) + e2 * (r2 * math.sin(ph) * fold)
            pts.append(mx(p, sx))
            if k == 0:
                ws.append({"Spine": 0.35, UA: 0.65})
            else:
                ws.append({UA: 1 - wf, FA: wf})
        allpts.append(pts)
        rings.append((pts, ws))
    ring0 = match_ring(mb, armhole(T, sx), allpts[0])
    for vid in ring0:
        mb.w[vid] = {"Spine": 0.8, UA: 0.2}
    rr = [ring0] + [mb.ring(p, w) for p, w in rings]
    loft(mb, rr, "sleeve", "sleeve", seam=0, bake=(sx > 0))
    # манжета → край перчатки (кисть в кармане не видна)
    gr = [rr[-1]]
    for k, (c, r1, r2) in enumerate(GLOVE):
        t, e1, e2 = fr[len(SLEEVE) + k]
        pts = [mx(Vector(c) + e1 * (r1 * math.cos(rad(36 * j))) + e2 * (r2 * math.sin(rad(36 * j))), sx)
               for j in range(SL_N)]
        gr.append(mb.ring(pts, {FA: 0.3, HD: 0.7}))
    loft(mb, gr, "glove", "glove", seam=0, bake=(sx > 0))                  # торец резинки и перчатка из-под неё
    dark_cap(mb, gr[-1], mx(GLOVE[-1][0], sx), 0.4, (0, 0, 0), mx(Vector(GLOVE[-1][0]) - Vector(GLOVE[0][0]), sx))


# =====================================================================================
#  Карман-кенгуру: накладная «подушка» поверх живота, оттопырена кистями; боковые входы — тёмные щели
# =====================================================================================
PK_TOP, PK_BOT = 1.122, 0.915                    # верх кармана (307 px) и низ — на резинке
PK_HW_TOP, PK_HW_BOT = 0.128, 0.190              # полуширина вверху / внизу (±50 / ±74 px)
PK_NU, PK_NV = 6, 4


def hand_bump(x, z):
    """Объём кистей в кармане: «колбаски» от запястья к кончикам пальцев, по одной на сторону."""
    best = 0.0
    for sx in (1, -1):
        a = Vector((sx * WR.x, WR.z)); b = Vector((sx * HT.x, HT.z)); p = Vector((x, z))
        ab = b - a
        t = clamp((p - a).dot(ab) / ab.length_squared, 0, 1)
        d = (p - (a + ab * t)).length
        best = max(best, math.exp(-(d / 0.055) ** 2) * (1.0 - 0.25 * t))
    return best


def pocket_off(x, z):
    return 0.006 + 0.044 * hand_bump(x, z)


def build_pocket(mb):
    W = {"Spine": 1.0}
    top, base = [], []
    for iv in range(PK_NV + 1):
        v = iv / PK_NV
        z = lerp(PK_BOT, PK_TOP, v)
        hw = lerp(PK_HW_BOT, PK_HW_TOP, v ** 0.8)
        rt, rb = [], []
        for iu in range(PK_NU + 1):
            x = lerp(-hw, hw, iu / PK_NU)
            y0 = torso_front_y(x, z)
            off = pocket_off(x, z)
            if iv == PK_NV or iv == 0:                    # верх и низ пришиты: подушка сходит на нет
                off *= 0.35
            rt.append(mb.vert((x, y0 - off, z), W)); rb.append(mb.vert((x, y0 + 0.004, z), W))
        top.append(rt); base.append(rb)
    loft(mb, top, "pocket", "pocket", closed=False, inside=Vector((0, 0.0, 1.0)))
    # кромки: верх и низ — ткань, бока — тёмные входы (туда уходят рукава)
    loft(mb, [base[-1], top[-1]], "pocket_edge", "pocket", closed=False, direction=Vector((0, 0, 1)))
    loft(mb, [top[0], base[0]], "pocket_edge", "pocket", closed=False, direction=Vector((0, 0, -1)))
    for sx, iu in ((1, PK_NU), (-1, 0)):
        side_t = [top[iv][iu] for iv in range(PK_NV + 1)]
        side_b = [base[iv][iu] for iv in range(PK_NV + 1)]
        fis = loft(mb, [side_t, side_b], "pocket_mouth", "mouth", closed=False, direction=Vector((sx, 0, 0)))
        mb.flat_uv(fis)


# =====================================================================================
#  Капюшон: оболочка (те же 18 колонок, что у торса), спереди — проём; край подвёрнут; внутри — чёрная чаша
# =====================================================================================
# z, полуширина a, вперёд bf, назад bb, центр yc, проём: (полуширина w, край по Y) или None / "close"
# Спереди проём ±43.5 px (строки 108-120), верх 75 px, низ (V под «подбородком») 174 px; сбоку край капюшона
# от козырька 762 px (строка 72) до 728 px (строка 174); сзади капюшон ±50 px, макушка — 42 px.
HOOD = [
    (1.478, 0.128, 0.085, 0.115, -0.010, "close"),           # низ проёма — точка V
    (1.509, 0.118, 0.120, 0.114, -0.014, (0.050, -0.113)),
    (1.539, 0.114, 0.124, 0.114, -0.019, (0.073, -0.130)),
    (1.570, 0.120, 0.126, 0.118, -0.026, (0.093, -0.141)),
    (1.601, 0.127, 0.128, 0.125, -0.033, (0.111, -0.150)),
    (1.631, 0.127, 0.132, 0.130, -0.034, (0.110, -0.155)),
    (1.662, 0.122, 0.134, 0.135, -0.035, (0.091, -0.160)),
    (1.693, 0.108, 0.134, 0.135, -0.037, (0.058, -0.168)),
    (1.716, 0.097, 0.138, 0.134, -0.037, "close"),           # верх проёма — козырёк
    (1.750, 0.082, 0.110, 0.110, -0.033, None),
    (1.778, 0.056, 0.085, 0.085, -0.017, None),
]
HOOD_TOP = (0.0, -0.004, 1.800)
HOOD_LIFT = {1.478: 0.036, 1.509: 0.022, 1.539: 0.010}  # низ капюшона по бокам и сзади лежит выше (на плечах)
RIM_BACK = 0.30                                  # края проёма по бокам уходят назад (проём — «ковш», не плоскость)


def hood_weight(z):
    k = smooth((z - 1.465) / 0.09)
    return {"Head": k, "Spine": 1 - k} if k < 1 else {"Head": 1.0}


def solve_th(a, n, x):
    """Угол суперэллипса, при котором |x| = x (передняя половина)."""
    q = clamp(x / a, 0.0, 0.999)
    s = q ** (n / 2.0)                       # x = a * sin^(2/n)  →  sin = (x/a)^(n/2)
    return math.degrees(math.asin(s))


def build_hood(mb, T):
    rings = [T[-1]]
    opened = []
    for z, a, bf, bb, yc, op in HOOD:
        n = 2.2
        W = hood_weight(z)
        lift = HOOD_LIFT.get(z, 0.0)
        zc = lambda d: z + lift * smooth(abs(d) / 70.0)
        if isinstance(op, tuple):
            w, yr = op
            thm = solve_th(a, n, w + 0.014)
            sides = [thm + (d - SIDE_D[0]) / (SIDE_D[-1] - SIDE_D[0]) * (SIDE_D[-1] - thm) for d in SIDE_D]
        else:
            sides = list(SIDE_D)
        ids = [None] * NC
        cx, cy = sellipse(a, bf, bb, yc, 0.0, n)
        ids[CI[0]] = mb.vert((0.0, cy, zc(0)), W)
        for sx in (1, -1):
            for d0, d in zip(SIDE_D, sides):
                x, y = sellipse(a, bf, bb, yc, rad(sx * d), n)
                ids[CI[sx * d0]] = mb.vert((x, y, zc(d)), W)
            if op == "close":
                ids[CI[sx * 18]] = ids[CI[0]]
            elif isinstance(op, tuple):
                ids[CI[sx * 18]] = mb.vert((sx * w, yr + RIM_BACK * w, z), W)
            else:
                x, y = sellipse(a, bf, bb, yc, rad(sx * 18), n)
                ids[CI[sx * 18]] = mb.vert((x, y, zc(18)), W)
        x, y = sellipse(a, bf, bb, yc, math.pi, n)
        ids[CI[180]] = mb.vert((0.0, y, zc(180)), W)
        rings.append(ids)
        opened.append(op)
    pole = mb.vert(HOOD_TOP, {"Head": 1.0})
    # проём: между колонками -18..0..18 от кольца «close» внизу до «close» вверху
    i0 = 1 + [k for k, op in enumerate(opened) if op == "close"][0]
    i1 = 1 + [k for k, op in enumerate(opened) if op == "close"][1]
    front = {(CI[18], CI[0]), (CI[0], CI[18]), (CI[-18], CI[0]), (CI[0], CI[-18])}

    def skip(i, j0, j1):
        return i0 <= i < i1 and (j0, j1) in front

    loft(mb, rings, "hood", "hood", seam=CI[180], skip=skip, pole=pole, inside=Vector((0, -0.03, 1.60)))
    # контур проёма: V внизу → левый край вверх → козырёк → правый край вниз
    loop = [rings[i0][CI[0]]] + [rings[i][CI[18]] for i in range(i0 + 1, i1)] + [rings[i1][CI[0]]] + \
           [rings[i][CI[-18]] for i in range(i1 - 1, i0, -1)]
    P = [mb.co[i] for i in loop]
    C = sum(P, Vector((0, 0, 0))) / len(P)
    back = Vector((0, 1, 0.08)).normalized()
    # подвёрнутый край (толстая двойная ткань ~3 см): внутрь проёма и назад — чернота начинается в глубине
    lip = mb.ring([p + (C - p) * 0.10 + back * 0.034 for p in P], [dict(mb.w[i]) for i in loop])
    loft(mb, [loop, lip], "hood_rim", "hood_rim", inside=C + back * 0.2)
    # «провал»: чёрная чаша вглубь капюшона (отдельный материал AnonimVoid, без запекания)
    deep = mb.ring([p + (C - p) * 0.50 + back * 0.095 for p in P], [dict(mb.w[i]) for i in loop])
    vp = mb.vert(C + back * 0.135, {"Head": 1.0})
    fis = loft(mb, [lip, deep], "void", "void", mat=1, bake=False, pole=vp, inside=C + back * 0.3)
    mb.flat_uv(fis)
    return rings


# =====================================================================================
#  Джинсы прямого кроя и грубые ботинки
# =====================================================================================
PYC = -0.005
P_RINGS = [(0.935, 0.193, 0.112, 0.110), (0.845, 0.205, 0.112, 0.102), (0.760, 0.207, 0.108, 0.098)]
CROTCH_Z = 0.706
LEG = [  # z, центр x, центр y, радиус по x, по y (спереди — ширина штанины, сбоку — профиль; голень чуть назад)
    (0.700, 0.110, 0.000, 0.098, 0.100),
    (0.620, 0.112, 0.000, 0.096, 0.097),
    (0.550, 0.118, 0.010, 0.088, 0.096),
    (0.478, 0.124, 0.017, 0.083, 0.094),    # колено
    (0.400, 0.130, 0.030, 0.081, 0.091),
    (0.330, 0.134, 0.038, 0.079, 0.089),
    (0.250, 0.134, 0.040, 0.079, 0.087),
    (0.190, 0.133, 0.040, 0.080, 0.089),    # гармошка на ботинке
    (0.150, 0.133, 0.038, 0.080, 0.092),
    (0.122, 0.133, 0.036, 0.079, 0.094),    # край джинсов на ботинке
]


def thigh_w(x, z):
    k = 0.9 * smooth((0.86 - z) / 0.2) * smooth(abs(x) / 0.1)
    if k <= 0:
        return {"Pelvis": 1.0}
    return {"Pelvis": 1 - k, ("ThighL" if x > 0 else "ThighR"): k}


def build_jeans(mb):
    rings = []
    for z, a, bf, bb in P_RINGS:
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
        for k, (z, cx, cy, rx, ry) in enumerate(LEG):
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
        z, cx, cy = LEG[-1][0], LEG[-1][1], LEG[-1][2]
        dark_cap(mb, lr[-1], (sx * cx, cy, z), 0.5, (0, 0, 0.03), (0, 0, -1))


def setup_boot_globals():
    ang = rad(12)
    Y["BOOT_A"] = Vector((0.133, 0.040, 0.0)); Y["BOOT_ANG"] = ang
    Y["BOOT_F"] = Vector((math.sin(ang), -math.cos(ang), 0)); Y["BOOT_O"] = Vector((math.cos(ang), math.sin(ang), 0))
    Y["SOLE_Z"] = 0.034                                                         # массивная подошва (~13 px)
    Y["SOLE_SPEC"] = (0.072, 0.162, 0.162, 0.063, 0.053, 3.0)                    # носок +0.234, пятка -0.090 (сбоку)
    Y["BOOT_SPEC"] = [
        (0.035, 0.072, 0.154, 0.155, 0.059, 0.049, 3.0),
        (0.058, 0.071, 0.152, 0.154, 0.060, 0.050, 3.0),     # борт
        (0.084, 0.062, 0.140, 0.146, 0.057, 0.050, 2.6),     # верх носка (высокий носок трекинговых)
        (0.104, 0.042, 0.116, 0.128, 0.053, 0.050, 2.4),     # подъём
        (0.122, 0.022, 0.086, 0.104, 0.051, 0.050, 2.3),     # шнуровка
        (0.140, 0.012, 0.064, 0.080, 0.052, 0.052, 2.2),     # мягкий кант
        (0.175, 0.006, 0.054, 0.058, 0.050, 0.050, 2.0),     # под джинсами
    ]


def build_all():
    mb = MB()
    T = build_torso(mb)
    for sx in (1, -1):
        build_arm(mb, T, sx)
    build_pocket(mb)
    build_hood(mb, T)
    build_jeans(mb)
    setup_boot_globals()
    for sx in (1, -1):
        Y["build_boot"](mb, sx)
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
            if d.users == 0 and (d.name.startswith(NAME) or d.name.startswith("AnPrev") or d.name.startswith("Yurchik")):
                blk.remove(d)
    for ac in list(bpy.data.actions):
        if ac.name.startswith(NAME + "_"):
            bpy.data.actions.remove(ac)


def make_void_material():
    """«Провал» под капюшоном: чистый чёрный без света. В glTF — KHR_materials_unlit (в Godot — unshaded)."""
    m = bpy.data.materials.get(NAME + "Void") or bpy.data.materials.new(NAME + "Void")
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0, 0, 0, 1); bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    m.diffuse_color = (0, 0, 0, 1)
    m.specular_intensity = 0.0
    m.roughness = 1.0
    m.use_backface_culling = False
    return m


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


def load_rgb(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    a = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)[::-1, :, :3].copy()


def save_rgb(a, path):
    h, w = a.shape[:2]
    img = bpy.data.images.new("AnPrevCmp", w, h, alpha=True)
    o = np.ones((h, w, 4), np.float32); o[..., :3] = a
    img.pixels.foreach_set(np.ascontiguousarray(o[::-1]).ravel())
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)


def compare(tag, outs):
    """Референс и рендер рядом, в одном масштабе (1 px = T_S м): спереди / сбоку / сзади."""
    ref = load_rgb(REF_TURN)
    H, W = ref.shape[:2]
    pairs = []
    for name, cx in (("front", T_CXF), ("side", T_CXS), ("back", T_CXB)):
        r = load_rgb(os.path.join(PREVIEW, "anonim_%s_%s.png" % (tag, name)))
        rh, rw = r.shape[:2]
        crop = np.full((rh, rw, 3), 0.6, np.float32)
        y0 = int(T_GY + 20 - rh); x0 = int(cx - rw / 2)
        for yy in range(rh):
            sy = y0 + yy
            if 0 <= sy < H:
                xa, xb = max(x0, 0), min(x0 + rw, W)
                crop[yy, xa - x0:xb - x0] = ref[sy, xa:xb]
        pairs += [crop, r, np.full((rh, 14, 3), 1.0, np.float32)]
    out = os.path.join(PREVIEW, "anonim_%s_compare.png" % tag)
    save_rgb(np.concatenate(pairs[:-1], axis=1), out)
    return out


def preview(sc, tag):
    """Ортографические рендеры в масштабе тёрнэраунда + ракурсы в капюшон (снизу, сбоку)."""
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
        sc.world = bpy.data.worlds.new("AnPrevWorld")
    sc.world.color = (0.55, 0.56, 0.60)
    cam_d = bpy.data.cameras.new("AnPrevCam")
    cam = bpy.data.objects.new("AnPrevCam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
    refs = [o for o in sc.objects if o.name.startswith("YurchikRef_")]
    outs = []
    H = int(T_GY - T_TOP + 40)
    # имя, направление на камеру, разрешение, цель, орто-масштаб (None — масштаб тёрнэраунда; <0 — перспектива)
    shots = [("front", Vector((0, -1, 0)), (500, H), None, None),
             ("side", Vector((-1, 0, 0)), (500, H), None, None),
             ("back", Vector((0, 1, 0)), (500, H), None, None),
             ("hood_below", Vector((0.0, -1.0, -0.75)), (600, 600), Vector((0, -0.08, 1.58)), -0.9),
             ("hood_side", Vector((0.85, -1.0, -0.15)), (600, 600), Vector((0, -0.06, 1.60)), -0.9),
             ("hood_front", Vector((0.0, -1.0, 0.05)), (600, 600), Vector((0, -0.06, 1.58)), 0.62),
             ("q34", Vector((0.7, -1, 0.12)), (700, 1000), Vector((0, 0, 0.92)), 2.05),
             ("q34back", Vector((-0.8, 1, 0.12)), (700, 1000), Vector((0, 0, 0.92)), 2.05),
             ("pocket", Vector((0.55, -1, -0.10)), (700, 600), Vector((0, -0.06, 1.08)), 0.75),
             ("withyur", Vector((0.15, -1, 0.05)), (900, 1000), Vector((0.45, 0, 0.92)), 2.15)]
    for name, d, (rw, rh), tgt, osc in shots:
        d = d.normalized()
        for o in refs:
            o.hide_render = name != "withyur"
        sc.display.shading.light = 'STUDIO' if (STAGE == "geo" or name not in ("front", "side", "back")) else 'FLAT'
        sc.render.resolution_x, sc.render.resolution_y = rw, rh
        if osc is None:
            cam_d.type = 'ORTHO'; cam_d.ortho_scale = max(rw, rh) * T_S
            tgt = Vector((0, 0, (rh / 2 - 20) * T_S))
            dist = 6.0
        elif osc < 0:
            cam_d.type = 'PERSP'; cam_d.lens = 50; dist = -osc
        else:
            cam_d.type = 'ORTHO'; cam_d.ortho_scale = osc; dist = 6.0
        cam.location = tgt + d * dist
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(PREVIEW, "anonim_%s_%s.png" % (tag, name))
        bpy.ops.render.render(write_still=True)
        outs.append(sc.render.filepath)
    bpy.data.objects.remove(cam, do_unlink=True)
    for o in refs:
        o.hide_render = False
    outs.append(compare(tag, outs))
    return outs


# =====================================================================================
def main():
    sc = get_scene()
    clear_own(sc)
    mb = build_all()
    Y["ISL_DENS"].update(ISL_DENS_A)
    D, pos = Y["pack_islands"](mb, size=ATLAS)
    mats = [Y["make_material"](NAME + "Mat", None, False), make_void_material()]
    mats[0].diffuse_color = (0.42, 0.42, 0.43, 1)
    body, fsel, used = Y["make_object"](mb, 0, NAME + "Mesh", sc.collection, mats)
    tri = lambda pred: sum(len(mb.faces[f]) - 2 for f in fsel if pred(f))
    parts = {}
    for f in fsel:
        parts[mb.fisl[f]] = parts.get(mb.fisl[f], 0) + len(mb.faces[f]) - 2
    info = {"stage": STAGE, "height": round(max(p.z for p in mb.co), 3), "tris": tri(lambda f: True),
            "parts": parts, "verts": len(used), "density_px_per_m": round(D, 1)}
    sys.path.insert(0, HERE); import ps2_budget
    info["budget"] = ps2_budget.check(NAME, info["tris"], "character")
    add_yurchik(sc)
    info["previews"] = preview(sc, STAGE)
    return info


ISL_DENS_A = {"torso": 1.0, "sleeve": 1.0, "glove": 1.2, "pocket": 1.1, "pocket_edge": 0.8, "pocket_mouth": 0.3,
              "hood": 1.0, "hood_rim": 0.9, "void": 0.2, "pelvis": 0.5, "legL": 0.85, "legR": 0.85, "boot": 1.1,
              "sole": 0.6, "sole_cap": 0.3, "dark": 0.3}

result = main()
