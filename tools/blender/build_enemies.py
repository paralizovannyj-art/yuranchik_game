# -*- coding: utf-8 -*-
# Враги: офники (околофутбол, 3 расцветки одной модели) и Сергей (здоровяк в длинном пуховике с капюшоном).
#
# Модели собираются из тех же «деталей», что и Юрчик (tools/blender/build_yurchik_v3.py): торс, рукава, штаны,
# ботинки, голова — но без волос, сумки и молотка, с другой одеждой. Текстуры — полностью процедурные
# (никаких концептов), свет «запечён» в текстуру. Скелет и анимации — те же, что у Юрчика
# (Quaternius Universal Animation Library, CC0), перенос — функциями из retarget_ual_yurchik.py.
#
# Запуск (Blender 5.2, из корня проекта):
#   blender -b --factory-startup --python tools/blender/build_enemies.py -- enemy
#   blender -b --factory-startup --python tools/blender/build_enemies.py -- sergey
# Результат: assets/models/enemy.gltf (+ assets/textures/enemy_a|b|c.png), assets/models/sergey.gltf (+ sergey.png).
# Третий аргумент — папка для превью-рендеров (необязательно).
import bpy, os, sys, math, json, contextlib
import numpy as np
from mathutils import Vector, Matrix, Quaternion

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["enemy"]
WHO = ARGS[0]
PREVIEW = ARGS[1] if len(ARGS) > 1 else None


def load(name, cut):
    src = open(os.path.join(HERE, name), encoding="utf-8").read()
    ns = {"YUR_ROOT": ROOT, "__file__": os.path.join(HERE, name)}
    exec(compile(src[:src.rindex(cut)], name, "exec"), ns)
    return ns


Y = load("build_yurchik_v3.py", "\nresult = main()")
R = load("retarget_ual_yurchik.py", "\nstats = main()")
vnoise, fbm, col, smooth, clamp, rad = Y["vnoise"], Y["fbm"], Y["col"], Y["smooth"], Y["clamp"], Y["rad"]
MB, loft, dark_cap, T_COLS, T_IDX = Y["MB"], Y["loft"], Y["dark_cap"], Y["T_COLS"], Y["T_IDX"]
JS = np.array(Y["JS"], np.float32); AD = np.array(Y["AD"], np.float32); AN = np.array(Y["AN"], np.float32)
HYC = Y["HYC"]


def _sel(sc, obs, active):
    for o in bpy.context.scene.objects:
        o.select_set(o in obs)
    bpy.context.view_layer.objects.active = active


Y["select_only"] = _sel
Y["scene_ctx"] = lambda sc: contextlib.nullcontext()
Y["RLEG_OVR"] = {}                                   # у Юрчика правая штанина стянута бинтом — врагам не надо

SRCS = {"UAL1": os.path.join(HERE, "ual", "UAL1_Standard.glb"), "UAL2": os.path.join(HERE, "ual", "UAL2_Standard.glb")}
CLIPS = [
    ("Idle", "UAL1", "Idle_Loop", False),
    ("Walk", "UAL1", "Walk_Loop", False),
    ("Run", "UAL1", "Jog_Fwd_Loop", False),
    ("Shamble", "UAL2", "Zombie_Walk_Fwd_Loop", False),
    ("ZombieIdle", "UAL2", "Zombie_Idle_Loop", False),
    ("Punch", "UAL1", "Punch_Cross", False),
    ("Hook", "UAL2", "Melee_Hook", False),
    ("Scratch", "UAL2", "Zombie_Scratch", False),
    ("Grab", "UAL1", "Push_Loop", False),
    ("HitChest", "UAL1", "Hit_Chest", False),
    ("HitHead", "UAL1", "Hit_Head", False),
    ("Knockback", "UAL2", "Hit_Knockback", False),
    ("Death", "UAL1", "Death01", False),
    ("GetUp", "UAL2", "LayToIdle", False),
    ("Crouch", "UAL1", "Crouch_Idle_Loop", False),
]


# =====================================================================================
#  Геометрия
# =====================================================================================
def drop_faces(mb, pred):
    keep = [i for i in range(len(mb.faces)) if not pred(i)]
    for attr in ("faces", "fuv", "fisl", "ftag", "fmat", "fbake", "fobj"):
        setattr(mb, attr, [getattr(mb, attr)[i] for i in keep])


def build_skirt(mb, T):
    """Длинные полы пуховика — от подола куртки до колен. Веса: таз → бёдра (левая половина за левой ногой)."""
    hem = T[8]
    rings = [hem]
    yc = -0.012
    for z, grow in ((0.70, 1.035), (0.585, 1.065), (0.475, 1.085)):
        ids = []
        for vid in hem:
            p = mb.co[vid]
            x = p.x * grow; y = yc + (p.y - yc) * grow
            k = 0.88 * smooth((0.84 - z) / 0.26)
            side = clamp(x / 0.07, -1, 1)
            ids.append(mb.vert((x, y, z), {"Pelvis": 1 - k, "ThighL": k * (0.5 + 0.5 * side), "ThighR": k * (0.5 - 0.5 * side)}))
        rings.append(ids)
    loft(mb, rings, "skirt", "skirt", seam=T_IDX["R90"], inside=Vector((0, -0.01, 0.6)))
    dark_cap(mb, rings[-1], (0, yc, 0.475), 0.5, (0, 0, 0.04), (0, 0, -1))


HU_COLS = [0, 22, 45, 70, 100, 135, 180, -135, -100, -70, -45, -22]


def build_hood_up(mb):
    """Надетый капюшон: оболочка вокруг головы с вырезом для лица."""
    yc = -0.040
    # z, полуширина, вперёд, назад, вес Head
    spec = [(1.455, 0.118, 0.105, 0.128, 0.0), (1.520, 0.124, 0.118, 0.136, 0.5), (1.590, 0.128, 0.132, 0.140, 1.0),
            (1.660, 0.128, 0.142, 0.140, 1.0), (1.730, 0.120, 0.146, 0.132, 1.0), (1.790, 0.094, 0.120, 0.104, 1.0),
            (1.825, 0.052, 0.068, 0.058, 1.0)]
    rings = []
    for z, a, bf, bb, wh in spec:
        pts = []
        for deg in HU_COLS:
            x, y = Y["sellipse"](a, bf, bb, yc, rad(deg), 2.2)
            pts.append((x, y, z))
        rings.append(mb.ring(pts, {"Head": wh, "Spine": 1 - wh}))
    pole = mb.vert((0, yc + 0.004, 1.838), {"Head": 1.0})

    def skip(i, j0, j1):                              # вырез: спереди, от груди до лба
        return i <= 3 and abs(HU_COLS[j0]) <= 45 and abs(HU_COLS[j1]) <= 45

    loft(mb, rings, "hoodup", "hoodup", seam=6, pole=pole, skip=skip, inside=Vector((0, yc, 1.62)))


def build_mesh(sergey):
    mb = MB()
    T = Y["build_torso"](mb)
    Y["build_arm"](mb, T, 1); Y["build_arm"](mb, T, -1)
    Y["build_pants"](mb)
    Y["build_boot"](mb, 1); Y["build_boot"](mb, -1)
    Y["build_head"](mb); Y["build_neck"](mb); Y["build_beanie"](mb)
    if sergey:
        build_skirt(mb, T)
        build_hood_up(mb)
    else:
        Y["build_hood"](mb)
    drop_faces(mb, lambda i: mb.ftag[i] == "band_tail" or mb.fisl[i].startswith("pocket"))
    mb.fmat = [0] * len(mb.faces)
    mb.fobj = [0] * len(mb.faces)
    return mb


# =====================================================================================
#  Раскраска
# =====================================================================================
def toplight(N, lo=0.70):
    """Запечённый свет сверху-спереди — как в играх эпохи PS2."""
    return (lo + (1 - lo) * np.clip(N[:, 2] * 0.55 - N[:, 1] * 0.25 + 0.5, 0, 1))[:, None]


def nsmooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def seg_dist(x, z, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    t = np.clip(((x - a[0]) * dx + (z - a[1]) * dz) / (dx * dx + dz * dz), 0, 1)
    return np.hypot(x - (a[0] + t * dx), z - (a[1] + t * dz))


def mix(c, c2, k):
    k = np.clip(k, 0, 1)
    if k.ndim == 1:
        k = k[:, None]
    return c * (1 - k) + c2 * k


def knit(base, u, v, n=48):
    return col(base) * (0.72 + 0.45 * (np.floor(u * n) % 2))[:, None]


def paint_jacket(V, tag, P, N, u, v):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    base = col(V["jacket"])
    c = base * (0.82 + 0.36 * fbm(x * 55 + z * 11, z * 55 + y * 35, 3))[:, None]
    rib = col(V["rib"])
    if tag == "sleeve":
        t = (P - JS) @ AD
        out = (P - JS) @ AN
        if V.get("quilt"):
            band = (t / 0.075) % 1.0
            c = c * (0.62 + 0.55 * np.sin(np.pi * band) ** 0.7)[:, None]
        else:
            c = c * (0.88 + 0.20 * np.sin(t * 75 + vnoise(u * 5, v * 3, 5) * 5))[:, None]       # складки
        c = np.where((t > 0.532)[:, None], rib * (0.7 + 0.5 * (np.floor(u * 40) % 2))[:, None], c)   # манжета
        if V.get("patch"):                                                                       # нашивка на плече
            m = (np.abs(t - 0.150) < 0.024) & (np.abs(y - 0.012) < 0.020) & (out > 0.02)
            inner = (np.abs(t - 0.150) < 0.019) & (np.abs(y - 0.012) < 0.015)
            diag = np.abs((t - 0.150) - (y - 0.012)) < 0.005
            pc = np.where((inner & ~diag)[:, None], col(V["patch"][0]), col(V["patch"][1]))
            c = np.where(m[:, None], pc, c)
        if V.get("sleeve_stripe"):                                                               # полоса вдоль рукава
            m = (np.abs(y - 0.012) < 0.011) & (out > 0.03) & (t < 0.53)
            c = np.where(m[:, None], col(V["sleeve_stripe"]), c)
    else:
        if V.get("quilt"):
            band = (z / 0.082) % 1.0
            c = c * (0.60 + 0.58 * np.sin(np.pi * band) ** 0.7)[:, None]
        if tag == "hoodie":
            if V.get("zipped", True):
                zipm = np.abs(x) < 0.0045
                c = np.where(zipm[:, None], col((0.34, 0.34, 0.36)) * (0.6 + 0.6 * (np.floor(z * 260) % 2))[:, None], c * 0.92)
            else:
                c = col(V["hoodie"]) * (0.8 + 0.35 * fbm(x * 90, z * 90, 23))[:, None]
                cord = (np.abs(np.abs(x) - 0.016) < 0.0028) & (z > 1.30)                         # шнурки капюшона
                c = np.where(cord[:, None], col((0.72, 0.72, 0.70)), c)
                c = c * (0.55 + 0.45 * nsmooth((z - 0.85) / 0.5))[:, None]
        if tag == "jacket_edge" and not V.get("zipped", True):
            c = c * 0.6
        if tag != "skirt" and not V.get("quilt"):
            c = np.where((z < 0.868)[:, None], rib * (0.7 + 0.5 * (np.floor(u * 150) % 2))[:, None], c)   # резинка снизу
            c = np.where((z > 1.447)[:, None], rib * (0.7 + 0.5 * (np.floor(u * 150) % 2))[:, None], c)   # ворот
        c = c * (0.74 + 0.26 * nsmooth((z - 0.45) / 0.9))[:, None]                                 # к низу темнее
        if V.get("back_print"):                                                                   # надпись-полоса на спине
            m = (N[:, 1] > 0.6) & (np.abs(z - 1.30) < 0.018) & (np.abs(x) < 0.11)
            c = np.where(m[:, None], col(V["back_print"]), c)
    return c * toplight(N)


def paint_face(V, P, N):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    ax = np.abs(x)
    th = np.degrees(np.arctan2(ax, -(y - HYC)))                    # 0 — лицо, 180 — затылок
    skin = col(V["skin"]) * (0.86 + 0.24 * fbm(x * 230, z * 230, 31))[:, None]
    skin = skin * (0.80 + 0.20 * np.clip(-N[:, 1], 0, 1))[:, None]
    eye_d = np.hypot((ax - 0.031) / 0.017, (z - 1.622) / 0.010)
    skin = skin * (1 - 0.42 * np.exp(-eye_d ** 2))[:, None]        # глазницы
    skin = skin * np.where((ax < 0.014) & (np.abs(z - 1.5745) < 0.0035), 0.5, 1.0)[:, None]     # тень под носом
    skin = skin * np.where((ax < 0.005) & (z > 1.585) & (z < 1.612), 1.12, 1.0)[:, None]        # переносица
    stub = np.clip((1.580 - z) / 0.02, 0, 1) * (th < 95)
    skin = mix(skin, col((0.27, 0.24, 0.23)), stub * 0.45)
    mouth = (ax < 0.023) & (np.abs(z - 1.5525 + 0.25 * ax) < 0.0021)
    skin = np.where(mouth[:, None], col((0.20, 0.10, 0.09)), skin)
    white = np.hypot((ax - 0.031) / 0.0125, (z - 1.6215) / 0.0050) < 1
    iris = np.hypot(ax - 0.0300, z - 1.6218) < 0.0050
    lid = (np.abs(z - 1.6272) < 0.0017) & (np.abs(ax - 0.031) < 0.0140)
    brow = seg_dist(ax, z, (0.011, 1.6325), (0.051, 1.6450)) < 0.0036      # брови домиком внутрь — злые
    c = skin
    c = np.where(white[:, None], col((0.72, 0.70, 0.67)), c)
    c = np.where(iris[:, None], col((0.07, 0.05, 0.045)), c)
    c = np.where((lid | brow)[:, None], col((0.09, 0.065, 0.055)), c)
    hair = (th > 68) & (z > 1.592 + 0.012 * np.cos(np.radians(th)))
    ear = (np.abs(th - 88) < 9) & (np.abs(z - 1.612) < 0.018)
    c = np.where(hair[:, None], col(V["hair"]) * (0.7 + 0.6 * vnoise(x * 600, z * 600, 41))[:, None], c)
    c = np.where((ear & ~hair)[:, None], col(V["skin"]) * 0.72, c)

    kind = V["face"]
    if kind == "balaclava":
        slit = (np.abs(z - 1.6235) < 0.0150 - 0.10 * np.clip(ax - 0.040, 0, 1)) & (th < 58)
        k = col(V["mask"]) * (0.72 + 0.5 * (np.floor(z * 420) % 2))[:, None] * (0.85 + 0.3 * fbm(x * 150, z * 150, 3))[:, None]
        edge = (np.abs(z - 1.6235) < 0.0185) & (th < 62) & ~slit
        k = np.where(edge[:, None], k * 0.55, k)
        c = np.where(slit[:, None], c, k)
    elif kind == "scarf":
        m = (z < 1.598 - 0.00012 * th) & (th < 125)
        band = np.floor((z - 1.5) / 0.0115 + 0.6 * vnoise(x * 25, z * 8, 17)) % 2
        s = np.where((band > 0)[:, None], col(V["scarf"][0]), col(V["scarf"][1]))
        s = s * (0.72 + 0.4 * fbm(x * 120, z * 120, 9))[:, None]
        c = np.where(m[:, None], s, c)
    elif kind == "medmask":
        top = 1.600 - 0.55 * ax ** 1.3
        m = (z < top) & (z > 1.532) & (th < 66)
        k = col(V["mask"]) * (0.85 + 0.25 * fbm(x * 140, z * 140, 13))[:, None]
        pleat = np.minimum.reduce([np.abs(z - zz) for zz in (1.586, 1.572, 1.558)]) < 0.0016
        k = np.where(pleat[:, None], k * 0.6, k)
        c = np.where(m[:, None], k, c)
        loop = (th >= 66) & (th < 92) & (np.abs(z - (1.588 + 0.0006 * (th - 66))) < 0.0020)
        c = np.where(loop[:, None], col((0.78, 0.78, 0.78)), c)
    elif kind == "dark":                                            # лицо в тени капюшона
        c = c * col((0.20, 0.19, 0.22))
        glint = np.hypot(ax - 0.0300, z - 1.6222) < 0.0026
        c = np.where(glint[:, None], col((0.60, 0.58, 0.52)), c)
    return c * toplight(N, 0.8)


def paint_neck(V, P, N, u, v):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    kind = V.get("neck", "skin")
    if kind == "knit":
        c = col(V["mask"]) * (0.72 + 0.5 * (np.floor(z * 420) % 2))[:, None]
    elif kind == "scarf":
        band = np.floor((z - 1.5) / 0.0115 + 0.6 * vnoise(x * 25, z * 8, 17)) % 2
        c = np.where((band > 0)[:, None], col(V["scarf"][0]), col(V["scarf"][1])) * (0.72 + 0.4 * fbm(x * 120, z * 120, 9))[:, None]
    else:
        c = col(V["skin"]) * (0.62 + 0.2 * fbm(x * 200, z * 200, 33))[:, None]
    return c * toplight(N, 0.75)


def paint_pants(V, P, N, u, v):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    front = np.clip(-N[:, 1], 0, 1)
    base = col(V["pants"])
    if V.get("pants_kind", "jeans") == "jeans":
        weave = 0.80 + 0.35 * vnoise(x * 520 + y * 310, z * 520, 9)
        wear = 0.30 * np.exp(-((z - 0.63) / 0.11) ** 2) * front + 0.36 * np.exp(-((z - 0.455) / 0.05) ** 2) * front
        c = base * (weave + wear)[:, None] + col((0.20, 0.21, 0.23)) * (wear * 0.35)[:, None]
        seam = (np.abs(N[:, 0]) > 0.90) & (np.abs(y + 0.008) < 0.0045)
        c = np.where(seam[:, None], c * 0.55, c)
        c = np.where((z < 0.150)[:, None], c * 1.28, c)                                           # подворот
    else:
        c = base * (0.82 + 0.3 * fbm(x * 80, z * 80, 19))[:, None]
        c = c * (0.9 + 0.16 * np.sin(z * 60 + vnoise(u * 4, v * 3, 7) * 5))[:, None]
        if V.get("pants_stripe"):
            m = (np.abs(N[:, 0]) > 0.80) & (np.abs(y + 0.008) < 0.013)
            c = np.where(m[:, None], col(V["pants_stripe"]), c)
        c = np.where((z < 0.135)[:, None], c * 0.7, c)                                            # манжета
    dirt = np.clip((0.30 - z) / 0.2, 0, 1) * fbm(x * 60, z * 60, 77)
    c = mix(c, col((0.16, 0.15, 0.14)), dirt * 0.7)
    c = c * (0.42 + 0.58 * np.clip((0.82 - z) / 0.09, 0, 1))[:, None]                             # тень под курткой
    return c * toplight(N)


def paint_boot(V, P, N, u, v):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    c = col(V["shoe"]) * (0.84 + 0.26 * fbm(x * 210, y * 210, 7))[:, None]
    acc = col(V["shoe2"])
    toe = y < -0.150
    heel = y > 0.062
    band = (np.abs((z - 0.085) - 0.42 * (y + 0.06)) < 0.011) & (np.abs(N[:, 2]) < 0.6) & (y > -0.13) & (y < 0.05)
    c = np.where((toe | heel | band)[:, None], acc * (0.85 + 0.25 * fbm(x * 210, y * 210, 8))[:, None], c)
    laces = (N[:, 2] > 0.40) & (y < -0.02) & (y > -0.125)
    c = np.where((laces & (np.floor(y * 150) % 2 == 0))[:, None], col(V.get("laces", (0.14, 0.14, 0.15))), c)
    c = np.where((z > 0.150)[:, None], col(V.get("sock", (0.06, 0.06, 0.07))), c)
    dirt = np.clip((0.085 - z) / 0.05, 0, 1) * (0.3 + 0.7 * fbm(x * 90, y * 90, 71))
    c = mix(c, col((0.20, 0.18, 0.16)), dirt * 0.8)
    return c * toplight(N)


def paint_hand2(V, tag, P, N, v):
    c = Y["paint_hand"](tag, P, N, v)
    lum = c.mean(axis=1, keepdims=True)
    if V.get("gloves"):
        return col(V["gloves"]) * (0.5 + 3.2 * lum)
    c = col(V["skin"]) * (0.45 + 1.6 * np.clip(lum, 0, 0.5))
    if V.get("knuckles"):                                           # сбитые костяшки
        d = P - np.array(Y["HAND_W"], np.float32)
        l = d @ np.array(Y["HAND_L"], np.float32)
        back = -(N @ np.array(Y["HAND_PN"], np.float32))
        k = np.exp(-((l - 0.092) / 0.014) ** 2) * np.clip(back, 0, 1)
        c = mix(c, col(V["knuckles"]), k * 0.85)
    return c


def make_painter(V, unscale=(1.0, 1.0, 1.0)):
    us = np.array(unscale, np.float32)

    def paint(tag, refs, P, N, LUV):
        P = P / us
        n = len(P); alpha = np.ones(n, np.float32)
        u, v = LUV[:, 0], LUV[:, 1]
        if tag in ("jacket", "jacket_edge", "hoodie", "sleeve", "skirt"):
            c = paint_jacket(V, tag, P, N, u, v)
        elif tag == "hood":
            c = col(V.get("hoodie", V["jacket"])) * (0.75 + 0.4 * fbm(P[:, 0] * 90, P[:, 2] * 90, 23))[:, None] * toplight(N)
        elif tag == "hoodup":
            z = P[:, 2]
            band = (z / 0.082) % 1.0
            c = col(V["jacket"]) * (0.62 + 0.55 * np.sin(np.pi * band) ** 0.7)[:, None]
            th = np.degrees(np.arctan2(np.abs(P[:, 0]), -(P[:, 1] + 0.04)))
            fur = (th < 58) & (z < 1.80) | ((z > 1.70) & (z < 1.745) & (th < 50))
            fc = col(V["fur"]) * (0.45 + 1.0 * vnoise(P[:, 0] * 700, z * 500, 3))[:, None]
            c = np.where(fur[:, None], fc, c) * toplight(N)
        elif tag == "pants":
            c = paint_pants(V, P, N, u, v)
        elif tag == "boot":
            c = paint_boot(V, P, N, u, v)
        elif tag == "sole":
            side = np.abs(N[:, 2]) < 0.5
            c = np.where(side[:, None], col(V["sole"]) * (0.8 + 0.3 * fbm(P[:, 0] * 90, P[:, 1] * 90, 5))[:, None],
                         col((0.07, 0.07, 0.07)) * np.ones((n, 1), np.float32))
            c = mix(c, col((0.19, 0.17, 0.15)), 0.5 * fbm(P[:, 0] * 70, P[:, 1] * 70, 15))
        elif tag == "face":
            c = paint_face(V, P, N)
        elif tag == "neck":
            c = paint_neck(V, P, N, u, v)
        elif tag == "beanie":
            c = knit(V["beanie"], u, v, 44) * (0.85 + 0.3 * fbm(u * 30, v * 30, 3))[:, None]
            if V.get("beanie_band"):
                c = np.where(((v > 0.20) & (v < 0.30))[:, None], col(V["beanie_band"]), c)
            c = np.where((v < 0.16)[:, None], c * 0.8, c) * toplight(N)
        elif tag in ("hand", "thumb"):
            c = paint_hand2(V, tag, P, N, v)
        else:
            c = np.tile(col((0.02, 0.02, 0.024)), (n, 1))
        return np.clip(c, 0, 1), alpha

    return paint


SKIN_A, SKIN_B = (0.60, 0.46, 0.40), (0.66, 0.52, 0.45)
VARIANTS = {
    # чёрный бомбер, балаклава, синие джинсы, белые кроссовки
    "enemy_a": dict(jacket=(0.050, 0.050, 0.058), rib=(0.035, 0.035, 0.04), zipped=True, patch=((0.80, 0.66, 0.10), (0.05, 0.05, 0.05)),
                    hoodie=(0.30, 0.30, 0.32), face="balaclava", mask=(0.045, 0.045, 0.05), neck="knit", skin=SKIN_A,
                    hair=(0.10, 0.08, 0.07), beanie=(0.045, 0.045, 0.05), pants=(0.17, 0.24, 0.40), pants_kind="jeans",
                    shoe=(0.80, 0.80, 0.78), shoe2=(0.52, 0.53, 0.56), sole=(0.74, 0.74, 0.72), gloves=(0.05, 0.05, 0.055)),
    # тёмно-синяя ветровка нараспашку, серое худи, шарф на лице, шапка с полосой
    "enemy_b": dict(jacket=(0.060, 0.085, 0.170), rib=(0.04, 0.05, 0.10), zipped=False, hoodie=(0.33, 0.33, 0.35),
                    sleeve_stripe=(0.78, 0.78, 0.76), face="scarf", scarf=((0.78, 0.76, 0.72), (0.42, 0.06, 0.07)), neck="scarf",
                    skin=SKIN_B, hair=(0.16, 0.12, 0.09), beanie=(0.05, 0.05, 0.06), beanie_band=(0.80, 0.78, 0.74),
                    pants=(0.10, 0.11, 0.13), pants_kind="jeans", shoe=(0.76, 0.76, 0.74), shoe2=(0.10, 0.10, 0.11),
                    sole=(0.70, 0.70, 0.68)),
    # оливковая ветровка, чёрное худи, медицинская маска, штаны с лампасом, чёрные кроссовки
    "enemy_c": dict(jacket=(0.165, 0.180, 0.105), rib=(0.10, 0.11, 0.07), zipped=False, hoodie=(0.055, 0.055, 0.06),
                    back_print=(0.72, 0.70, 0.62), face="medmask", mask=(0.06, 0.06, 0.07), neck="skin", skin=SKIN_A,
                    hair=(0.07, 0.06, 0.055), beanie=(0.26, 0.26, 0.28), pants=(0.055, 0.055, 0.062), pants_kind="track",
                    pants_stripe=(0.78, 0.78, 0.76), shoe=(0.07, 0.07, 0.075), shoe2=(0.16, 0.16, 0.17),
                    sole=(0.72, 0.72, 0.70), laces=(0.5, 0.5, 0.5), gloves=(0.05, 0.05, 0.055)),
}
SERGEY = dict(jacket=(0.060, 0.070, 0.082), rib=(0.03, 0.03, 0.035), zipped=True, quilt=True, fur=(0.30, 0.25, 0.20),
              face="dark", mask=(0.03, 0.03, 0.035), neck="knit", skin=(0.62, 0.56, 0.54), hair=(0.05, 0.05, 0.05),
              beanie=(0.03, 0.03, 0.035), pants=(0.045, 0.045, 0.05), pants_kind="track", shoe=(0.05, 0.05, 0.052),
              shoe2=(0.075, 0.075, 0.08), sole=(0.06, 0.06, 0.06), knuckles=(0.32, 0.05, 0.04))
SERGEY_SCALE = (1.20, 1.24, 1.0)                     # шире и толще; рост добавляется масштабом узла в игре


# =====================================================================================
#  Скелет, анимации, экспорт
# =====================================================================================
def rig(ob, used, mb, name):
    sc = bpy.context.scene
    arm_data = bpy.data.armatures.new(name + "Rig")
    arm = bpy.data.objects.new(name, arm_data)
    sc.collection.objects.link(arm)
    bpy.context.view_layer.update()
    _sel(sc, [arm], arm)
    bpy.ops.object.mode_set(mode='EDIT')
    for n, h, t, p in Y["BONES"]:
        b = arm_data.edit_bones.new(n)
        b.head = h; b.tail = t; b.roll = 0.0
        if p:
            b.parent = arm_data.edit_bones[p]
    bpy.ops.object.mode_set(mode='OBJECT')
    groups = {n: ob.vertex_groups.new(name=n) for n, *_ in Y["BONES"]}
    for k, vid in enumerate(used):
        w = {b: x for b, x in mb.w[vid].items() if x > 1e-4}
        tot = sum(w.values())
        for b, x in w.items():
            groups[b].add([k], x / tot, 'REPLACE')
    ob.parent = arm
    mod = ob.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
    return arm


def retarget(arm, clips):
    sc = bpy.context.scene
    sc.render.fps = R["FPS"]; sc.render.fps_base = 1.0
    arm.animation_data_create()
    MAP, NO_ALIGN = R["MAP"], R["NO_ALIGN"]
    order = [b.name for b in arm.data.bones if b.name in MAP]
    dw = arm.matrix_world
    dst_rest = {n: (dw @ arm.data.bones[n].matrix_local) for n in MAP}
    stats = {}
    for key, path in SRCS.items():
        cl = [c for c in clips if c[1] == key]
        if not cl:
            continue
        before = set(bpy.data.objects); before_actions = set(bpy.data.actions)
        bpy.ops.import_scene.gltf(filepath=path)
        imported = [o for o in bpy.data.objects if o not in before]
        src = [o for o in imported if o.type == 'ARMATURE'][0]
        src_actions = {a.name: a for a in bpy.data.actions if a not in before_actions}
        sad = src.animation_data or src.animation_data_create()
        for tr in list(sad.nla_tracks):
            sad.nla_tracks.remove(tr)
        sw = src.matrix_world
        src_rest = {n: (sw @ src.data.bones[n].matrix_local) for n in MAP.values()}

        def bdir(m):
            return (m.to_3x3() @ Vector((0, 1, 0))).normalized()

        q0 = {n: (Quaternion() if n in NO_ALIGN else R["rot_between"](bdir(dst_rest[n]), bdir(src_rest[s]))) for n, s in MAP.items()}
        hip_scale = arm.data.bones["Pelvis"].head_local.z / src.data.bones["pelvis"].head_local.z
        for name, _, sname, reverse, *rest in cl:
            sac = src_actions.get(sname) or next(a for n, a in src_actions.items() if n.split(".")[0] == sname)
            stats[name] = R["bake_clip"](sc, src, arm, sac, name, reverse, q0, src_rest, dst_rest, hip_scale, order,
                                         rest[0] if rest else None)
        for o in imported:
            bpy.data.objects.remove(o, do_unlink=True)
        for a in src_actions.values():
            bpy.data.actions.remove(a)
        for blk in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.images):
            for d in list(blk):
                if d.users == 0:
                    blk.remove(d)
    return stats


def export(arm, body, name):
    sc = bpy.context.scene
    _sel(sc, [arm, body], arm)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(ROOT, "assets", "models", name + ".gltf"), use_selection=True, use_active_scene=True,
        export_format='GLTF_SEPARATE', export_keep_originals=True, export_apply=False, export_skins=True,
        export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
        export_frame_step=1, export_optimize_animation_size=True, export_anim_single_armature=True,
        export_def_bones=False, export_reset_pose_bones=True, export_bake_animation=False)


def preview(name, body, height):
    """Быстрые рендеры спереди/сзади — чтобы проверить модель без открытия Blender."""
    if not PREVIEW:
        return
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'FLAT'; sc.display.shading.color_type = 'TEXTURE'
    sc.render.resolution_x, sc.render.resolution_y = 500, 900
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    w = bpy.data.worlds.new("W"); sc.world = w
    cam_d = bpy.data.cameras.new("C"); cam_d.type = 'ORTHO'; cam_d.ortho_scale = height * 1.12
    cam = bpy.data.objects.new("C", cam_d); sc.collection.objects.link(cam); sc.camera = cam
    for tag, d in (("front", Vector((0.25, -1, 0.1))), ("back", Vector((-0.45, 1, 0.1))), ("side", Vector((1, -0.15, 0.05)))):
        d = d.normalized()
        cam.location = Vector((0, 0, height * 0.5)) + d * 5
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(PREVIEW, "%s_%s.png" % (name, tag))
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)


def main():
    sc = bpy.context.scene
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    sergey = WHO == "sergey"
    name = "Sergey" if sergey else "Enemy"
    mb = build_mesh(sergey)
    scale = SERGEY_SCALE if sergey else (1.0, 1.0, 1.0)
    if sergey:
        for i, p in enumerate(mb.co):
            mb.co[i] = Vector((p.x * scale[0], p.y * scale[1], p.z * scale[2]))
        Y["BONES"] = [(n, tuple(a * s for a, s in zip(h, scale)), tuple(a * s for a, s in zip(t, scale)), p)
                      for n, h, t, p in Y["BONES"]]
    D, pos = Y["pack_islands"](mb)
    mat = Y["make_material"](name + "Mat", None, False)
    body, fsel, used = Y["make_object"](mb, 0, name + "Mesh", sc.collection, [mat])
    info = {"tris": sum(len(mb.faces[f]) - 2 for f in fsel), "verts": len(used), "density": round(D, 1)}

    variants = {"sergey": SERGEY} if sergey else VARIANTS
    first = None
    for tex_name, V in variants.items():
        Y["paint"] = make_painter(V, scale)
        rgba, Tb = Y["bake_atlas"](mb, {0: (body.data, fsel)}, None)
        img = Y["save_atlas"](rgba, tex_name)
        first = first or img
        if PREVIEW:
            Y["make_material"](name + "Mat", img, False)
            preview(tex_name, body, 1.9)
    Y["make_material"](name + "Mat", first, False)

    arm = rig(body, used, mb, name)
    info["clips"] = retarget(arm, CLIPS)
    export(arm, body, "sergey" if sergey else "enemy")
    print("BUILD_ENEMIES " + json.dumps(info))


main()
