# -*- coding: utf-8 -*-
"""Поза «Юрчик держит телефон правой рукой» — считается автоматически и уходит в игру (assets/models/phone_hold.json).

Как на референсах (references/hands/hold_photo_glove.webp — главный, hold_game_black.png, hold_game_pink.png):
телефон стоит вертикально, спинкой в ладони; четыре пальца обхватывают ЛЕВОЕ ребро и голыми кончиками ложатся на
лицевую сторону лесенкой (указательный у нижней части экрана, средний у софт-клавиш, безымянный у клавиш 4–7),
мизинец подогнут под нижний торец; большой палец — за правым верхним углом, смотрит вверх; тыл кисти — к камере,
запястье уходит в правый нижний угол кадра.

Поза не подгоняется руками: решатель (solve) ищет положение кисти и углы суставов так, чтобы
  * подушечки пальцев лежали на лицевой стороне у левого ребра на заданных высотах (TARGET_V),
  * ни одна фаланга и ладонь не входили в телефон (телефон — скруглённый брусок 56×111 мм, phone.gltf),
  * ладонь прилегала к спинке, большой палец — к правому ребру у TARGET_THUMB_V,
  * ни одна точка кисти не заслоняла экран (проверка лучами из камеры — occlusion()).
Считается всё в миллиметрах настоящего телефона: в игре телефон увеличен в SCALE раз (phone.gd), а кисть — в
HAND_SCALE раз (hand_scale в JSON). HAND_SCALE < SCALE — телефон в ладони чуть крупнее настоящего; в мм телефона
кисть уменьшена в HAND_K = HAND_SCALE / SCALE раз.

Запуск в Blender после tools/blender/build_yurchik_v3.py (сцена Yurchik3):
    ns = {"YUR_ROOT": r"<repo>"}; exec(open(r"<repo>/tools/blender/pose_phone_hold.py", encoding="utf-8").read(), ns)
    ns["run"]()      — решить позу, построить сцену PhonePose (камера как в игре), записать phone_hold.json,
                       отрендерить кадр из камеры в render_path (если задан)
"""
import json
import math
import os
import re

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = globals().get("YUR_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
POSE_JSON = os.path.join(ROOT, "assets", "models", "phone_hold.json")
PHONE_GLTF = os.path.join(ROOT, "assets", "models", "phone.gltf")
PHONE_GD = os.path.join(ROOT, "scripts", "ui", "phone.gd")
BUILD = os.path.join(ROOT, "tools", "blender", "build_yurchik_v3.py")
SCENE, SRC_SCENE = "PhonePose", "Yurchik3"

# Камера в осях скелета Godot при взгляде прямо (cam_pitch = −0.12): столбцы X, Y, Z и начало.
# Снято из игры: sk.global_transform.affine_inverse() * player.camera.global_transform.
CAM_G = ((-1.0, 0.0, 0.0), (0.0, 0.992809, 0.119712), (0.0, 0.119712, -0.99281), (0.0, 1.62, 0.182571))
CAM_FOV, RES = 72.0, (854, 480)

# Телефон (мм, оси узла Phone в Godot: u — вправо, v — вверх, w — к лицу): phone.gltf
PH_HX, PH_HY, PH_Z0, PH_Z1, PH_R = 28.2, 55.5, -9.35, 7.5, 3.0
SCREEN = (-23.4, 23.4, 2.6, 37.9)                  # прямоугольник экрана u0, u1, v0, v1 на лицевой стороне
# Высоты подушечек (мм от центра телефона), сняты с references/hands/hold_photo_glove.webp и hold_game_black.png:
# указательный — у нижней части экрана, средний — у софт-клавиш, безымянный — у клавиш 4–7 на лицевой стороне;
# мизинец подогнут под нижний торец и подпирает телефон снизу (UNDER).
TARGET_V = {"Index": 13.0, "Middle": -12.0, "Ring": -35.0, "Pinky": -62.0}   # лесенка сжата по HAND_K
# насколько подушечка заходит на лицевую сторону (u): кончики лежат на лице, а не на ребре; указательный —
# на рамке рядом с экраном, средний — на левой софт-клавише, безымянный — на столбце 1/4/7
TARGET_U = {"Index": -25.8, "Middle": -22.5, "Ring": -19.5}   # на 3 / 6 / 8 мм внутрь от ребра
TIP_DY = {"Index": -0.09, "Middle": -0.31, "Ring": -0.41}   # указательный почти горизонтален, ниже — круче (фото)
KNUCKLE_OUT = 17.0                                 # средний сустав выступает за левое ребро не больше чем на столько (мм)
UNDER = {"Pinky"}
PINKY_U = 3.0                                      # мизинец под торцом заходит к середине
TARGET_THUMB_V = 58.0                              # кончик большого пальца — у верхнего правого угла, смотрит вверх
THUMB_TIP = (0.7, -0.45)                            # кончик большого: (u, w) от заднего правого угла в радиусах пальца
THUMB_IP_MAX = 20.0                                # большой палец почти прямой (сгиб в межфаланговом ≤ 20°)
FINGERS = ["Index", "Middle", "Ring", "Pinky", "Thumb"]
POSE_BONES = ["HandR"] + [f"{n}R{k}" for n in FINGERS for k in (1, 2, 3)]


# ----------------------------------------------------------------------------- данные модели и игры
def _build_ns():
    """Таблицы кисти из build_yurchik_v3.py (без запуска сборки)."""
    src = open(BUILD, encoding="utf-8").read()
    ns = {"YUR_ROOT": ROOT}
    exec(compile(src[:src.rindex("\nresult = main()")], BUILD, "exec"), ns)
    return ns


def phone_consts():
    """OPEN_POS, OPEN_ROT (градусы) и SCALE — из scripts/ui/phone.gd, чтобы поза не устаревала."""
    s = open(PHONE_GD, encoding="utf-8").read()
    num = r"(-?[\d.]+)"
    pos = tuple(float(x) for x in re.search(r"OPEN_POS := Vector3\(" + ", ".join([num] * 3), s).groups())
    rot = tuple(float(x) for x in re.search(r"OPEN_ROT := Vector3\(" + ", ".join([r"deg_to_rad\(" + num + r"\)"] * 3), s).groups())
    scale = float(re.search(r"const SCALE := " + num, s).group(1))
    return pos, rot, scale


def hand_scale():
    """HAND_SCALE из phone.gd (масштаб кисти в игре); если его нет — как у телефона."""
    m = re.search(r"const HAND_SCALE := (-?[\d.]+)", open(PHONE_GD, encoding="utf-8").read())
    return float(m.group(1)) if m else phone_consts()[2]


def hand_k():
    """Во сколько раз кисть меньше в мм телефона, чем настоящая."""
    return hand_scale() / phone_consts()[2]


def g2b(v):
    """Godot (x, y, z) → Blender (x, −z, y)."""
    return Vector((v[0], -v[2], v[1]))


def cam_matrix():
    x, y, z, o = (g2b(c) for c in CAM_G)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = o
    return m


def phone_local():
    pos, rot, scale = phone_consts()
    rx, ry, rz = (math.radians(a) for a in rot)
    r = Matrix.Rotation(ry, 4, 'Y') @ Matrix.Rotation(rx, 4, 'X') @ Matrix.Rotation(rz, 4, 'Z')   # Godot YXZ
    return Matrix.Translation(pos) @ r @ Matrix.Scale(scale, 4)


def phone_to_arm():
    """мм телефона → координаты скелета (Blender): камера × узел телефона (оси камеры в Blender = оси в Godot)."""
    return cam_matrix() @ phone_local() @ Matrix.Scale(0.001, 4)


# ----------------------------------------------------------------------------- геометрия
def sdf_phone(P):
    """Знаковое расстояние (мм) до скруглённого бруска телефона, P[..., 3] в мм телефона."""
    c = np.array((0.0, 0.0, (PH_Z0 + PH_Z1) / 2)); h = np.array((PH_HX, PH_HY, (PH_Z1 - PH_Z0) / 2))
    q = np.abs(P - c) - h + PH_R
    return np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(axis=-1), 0) - PH_R


class Hand:
    """Кисть в мм телефона: начало (точка кисти l = w = p = 0) и оси L (к пальцам), W (к большому), P (к ладони)."""

    def __init__(self, Y, tilt, pitch, roll, o):
        self.Y = Y
        # базовая ориентация: пальцы влево (−u) с наклоном вверх tilt, большой палец вверх, ладонь к спинке телефона
        t = math.radians(tilt)
        L = np.array((-math.cos(t), math.sin(t), 0.0)); P = np.array((0.0, 0.0, 1.0))
        W = np.cross(L, P) * self.hand_sign()
        R = rot_about(W, math.radians(pitch)) @ rot_about(L, math.radians(roll))
        self.L, self.W, self.P = R @ L, R @ W, R @ P
        self.o = np.array(o, float)
        self.k = hand_k()

    def hand_sign(self):
        """Правая кисть — зеркальная копия левой: тройка (L, W, P) у неё левая. Знак W при W = ±(L × P)."""
        Y = self.Y
        Lr, Wr, Pr = (np.array(Y["mx"](v, -1)) for v in (Y["HAND_L"], Y["HAND_WD"], Y["HAND_PN"]))
        return float(np.sign(np.cross(Lr, Pr) @ Wr))

    def pt(self, lwp):
        lwp = np.asarray(lwp, float) * (1000.0 * self.k)
        return self.o + lwp[..., :1] * self.L + lwp[..., 1:2] * self.W + lwp[..., 2:3] * self.P


def rot_about(axis, a):
    axis = np.asarray(axis, float); axis = axis / np.linalg.norm(axis)
    K = np.array(((0, -axis[2], axis[1]), (axis[2], 0, -axis[0]), (-axis[1], axis[0], 0)))
    return np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K


# ----------------------------------------------------------------------------- пальцы: перебор по сетке
A1 = np.radians(np.arange(0, 96, 3.0)); A2 = np.radians(np.arange(0, 111, 3.0)); A3 = np.radians(np.arange(0, 81, 3.0))
SPREAD = np.radians(np.arange(-14, 15, 3.5))


def finger_fk(Y, name, a1, a2, a3, s):
    """Суставы пальца (кисть, м): костяшка, PIP, DIP, кончик. Углы — массивы одинаковой формы."""
    _, w, l0, segs, _ = next(f for f in Y["FINGERS"] if f[0] == name)
    K = np.array((l0, w, Y["KNUCKLE_P"]))
    shape = np.shape(a1)
    pts = [np.broadcast_to(K, shape + (3,))]
    acc = np.zeros(shape)
    for L, a in zip(segs, (a1, a2, a3)):
        acc = acc + a
        d = np.stack((np.cos(acc) * np.cos(s), np.cos(acc) * np.sin(s), np.sin(acc)), -1)
        pts.append(pts[-1] + d * L)
    return pts


def solve_finger(Y, hand, name, fine=False):
    """Лучшие углы (a1, a2, a3, spread) пальца для данной кисти и их стоимость."""
    r = next(f for f in Y["FINGERS"] if f[0] == name)[4] * 1000.0 * hand.k
    a1, a2, a3, s = np.meshgrid(A1, A2, A3, SPREAD, indexing="ij") if fine else \
        np.meshgrid(A1[::2], A2[::2], A3[::2], SPREAD[::2], indexing="ij")
    J = [hand.pt(p) for p in finger_fk(Y, name, a1, a2, a3, s)]
    cost = np.zeros(a1.shape)
    radii = (r * 1.0, r * 0.95, r * 0.78)
    for k in range(3):
        for t in (0.15, 0.4, 0.65, 0.9):
            q = J[k] + (J[k + 1] - J[k]) * t
            pen = radii[k] + 0.6 - sdf_phone(q)                     # 0.6 мм зазор
            cost += 40.0 * np.maximum(pen, 0) ** 2
    # подушечка ногтевой фаланги (середина фаланги, сдвиг к ладони): на лицевой стороне у левого края
    d3 = J[3] - J[2]
    pad = J[2] + d3 * 0.6
    tgt_v = TARGET_V[name]
    cost += 2.0 * (np.abs(sdf_phone(pad) - radii[2] - 0.6)) ** 2            # касается
    cost += 0.004 * np.degrees(s) ** 2                                    # пальцы сомкнуты, без веера
    # пальцы плотно обхватывают ребро: средний сустав (PIP) недалеко за левым краем, а не растопыренная «лапа»
    cost += 1.0 * np.maximum(-PH_HX - KNUCKLE_OUT - J[1][..., 0], 0) ** 2
    dn = d3 / (np.linalg.norm(d3, axis=-1, keepdims=True) + 1e-9)
    if name in UNDER:
        # мизинец — под нижним торцом: подушечка снизу, кончик смотрит вправо вдоль торца
        cost += 0.25 * (pad[..., 0] - PINKY_U) ** 2
        cost += 12.0 * dn[..., 1] ** 2                                    # вдоль торца, почти горизонтально
        cost += 3.0 * np.maximum(pad[..., 1] - (-PH_HY - radii[2] * 0.6), 0) ** 2
        cost += 0.5 * np.maximum(pad[..., 2] - PH_Z1, 0) ** 2 + 0.5 * np.maximum(PH_Z0 - pad[..., 2], 0) ** 2
        cost += 25.0 * np.maximum(0.6 - dn[..., 0], 0) ** 2
    else:
        cost += (1.0 if name == "Index" else 0.25) * (pad[..., 1] - tgt_v) ** 2     # указательный — выше остальных
        cost += 6.0 * (pad[..., 0] - TARGET_U[name]) ** 2
        cost += 3.0 * np.maximum(PH_Z1 - 1.0 - pad[..., 2], 0) ** 2           # на лице, а не на ребре
        cost += 3.0 * np.maximum(pad[..., 0] - (SCREEN[0] - radii[2] * 0.3), 0) ** 2   # не заходит на экран
        cost += 1.5 * np.maximum(-PH_HX + 1.5 - pad[..., 0], 0) ** 2          # и не висит за краем
        # ногтевая фаланга лежит на лицевой стороне и смотрит вправо и чуть вниз (как на референсе)
        cost += 25.0 * np.maximum(0.75 - dn[..., 0], 0) ** 2 + 300.0 * np.maximum(dn[..., 2], 0) ** 2  # не «в камеру»
        cost += 12.0 * (dn[..., 1] - TIP_DY[name]) ** 2                     # наклон кончика вниз — как на фото
    i = np.unravel_index(np.argmin(cost), cost.shape)
    return float(cost[i]), tuple(float(x[i]) for x in (a1, a2, a3, s))


# ----------------------------------------------------------------------------- большой палец
def _sdf_grad(p, h=0.05):
    g = np.array([sdf_phone(p + d) - sdf_phone(p - d) for d in np.eye(3) * h]) / (2 * h)
    return g / (np.linalg.norm(g) + 1e-9)


def solve_thumb(Y, hand):
    """Большой палец — цепочка из трёх фаланг (длины из модели) от основания в ладони до кончика на правом ребре
    у TARGET_THUMB_V. Суставы ищутся FABRIK: цепочка тянется к цели, суставы выталкиваются из телефона.
    Возвращает стоимость и суставы (мм телефона): основание, MCP, IP, кончик."""
    C = [np.array(c) for c, _ in Y["THUMB_J"]]
    lens = [float(np.linalg.norm(C[k + 1] - C[k])) * 1000 * hand.k for k in range(3)]
    rs = [r_ * 1000 * hand.k for _, r_ in Y["THUMB_J"]]
    base = hand.pt(C[0])
    # кончик — на правом ребре; высота такая, чтобы палец был почти прямой (~95 %) (в пределах верхней половины)
    # кончик — за задним правым углом: из камеры телефон частично закрывает палец (как на всех референсах)
    tu, tz = PH_HX + rs[3] * THUMB_TIP[0], PH_Z0 + rs[3] * THUMB_TIP[1]
    lat = (tu - base[0]) ** 2 + (tz - base[2]) ** 2
    tv = base[1] + math.sqrt(max((0.95 * sum(lens)) ** 2 - lat, 0.0))
    cost = 0.1 * (min(max(tv, 30.0), 60.0) - TARGET_THUMB_V) ** 2 + 2.0 * (tv - min(max(tv, 30.0), 60.0)) ** 2
    tip = np.array((tu, min(max(tv, 30.0), 60.0), tz))
    reach = float(np.linalg.norm(tip - base))
    cost += 0.5 * max(reach - sum(lens) * 0.97, 0) ** 2 + 0.5 * max(sum(lens) * 0.7 - reach, 0) ** 2
    # начальная цепочка — прямая с небольшим изгибом
    J = [base]
    out = np.array((0.35, 0.0, 1.0)); out /= np.linalg.norm(out)          # сгиб — к лицевой стороне, как у живого пальца
    for k, L in enumerate(lens):
        t = sum(lens[:k + 1]) / sum(lens)
        q = base + (tip - base) * t + out * (math.sin(t * math.pi) * 8.0)
        J.append(J[-1] + (q - J[-1]) / np.linalg.norm(q - J[-1]) * L)
    for _ in range(40):
        J[3] = tip.copy()                                                   # назад: от кончика
        for k in (2, 1, 0):
            d = J[k] - J[k + 1]; J[k] = J[k + 1] + d / np.linalg.norm(d) * lens[k]
        J[0] = base.copy()                                                  # вперёд: от основания
        for k in (1, 2, 3):
            d = J[k] - J[k - 1]; J[k] = J[k - 1] + d / np.linalg.norm(d) * lens[k - 1]
        for k in (1, 2):                                                    # суставы — вне телефона, но вплотную
            need = rs[k] * 0.95 + 0.8
            sd = sdf_phone(J[k])
            if sd < need:
                J[k] = J[k] + _sdf_grad(J[k]) * (need - sd)
            elif k == 2 or J[k][1] > -PH_HY * 0.4:                         # IP и MCP (если он у ребра) прижать
                J[k] = J[k] - _sdf_grad(J[k]) * (sd - need) * 0.5
    for k in range(3):
        for t in (0.25, 0.5, 0.75, 1.0):
            q = J[k] + (J[k + 1] - J[k]) * t
            cost += 40.0 * max(rs[k + 1] * 0.95 + 0.6 - sdf_phone(q), 0) ** 2
    cost += 0.5 * float(np.linalg.norm(J[3] - tip)) ** 2
    d3 = (J[3] - J[2]) / np.linalg.norm(J[3] - J[2])
    cost += 6.0 * max(0.6 - d3[1], 0) ** 2                                  # кончик смотрит вверх, вдоль ребра
    for k in (1, 2):                                       # MCP гнётся не больше ~80°, IP — почти прямой (референс)
        a = math.degrees(math.acos(np.clip(np.dot((J[k] - J[k - 1]) / lens[k - 1], (J[k + 1] - J[k]) / lens[k]), -1, 1)))
        cost += 0.01 * max(a - 80.0, 0) ** 2 if k == 1 else 0.3 * max(a - THUMB_IP_MAX, 0) ** 2
    return float(cost), J


# ----------------------------------------------------------------------------- кисть целиком
def palm_cost(Y, hand):
    """Ладонь не входит в телефон и прилегает к спинке; запястье — справа внизу, за телефоном."""
    c = 0.0
    for l, p, ww, tp, tb in Y["PALM"][1:]:
        for wq in np.linspace(-0.8, 0.8, 5):
            for pq, th in ((tp, 1), (-tb, -1)):
                q = hand.pt((l, ww * wq, p + pq * 0.8))
                pen = 1.0 - sdf_phone(q)
                c += 40.0 * max(pen, 0) ** 2
    mid = hand.pt((0.05, 0.0, 0.014))                                     # середина ладони — у спинки
    c += 0.5 * max(sdf_phone(mid) - 1.5, 0) ** 2
    wrist = hand.pt((-0.03, 0.0, 0.0))
    c += 0.05 * max(wrist[1] + 50.0, 0) ** 2 + 0.05 * max(15.0 - wrist[0], 0) ** 2   # запястье справа внизу
    # тыльная сторона кисти повёрнута к камере (широкая вязаная масса справа от телефона, как на фото):
    # ладонь смотрит влево (−u), пальцы уходят за левое ребро вглубь
    c += 60.0 * max(PALM_LEFT + float(hand.P[0]), 0) ** 2
    return c


PALM_LEFT = 0.35                                   # насколько ладонь повёрнута влево (−u): тыл кисти виден справа
THUMB_W = 0.3                                      # большой палец подстраивается под кисть, а не наоборот


def total(Y, prm, fine=False):
    hand = Hand(Y, *prm[:3], prm[3:])
    c = palm_cost(Y, hand)
    fing = {}
    for n in FINGERS[:4]:
        cf, a = solve_finger(Y, hand, n, fine)
        c += cf; fing[n] = a
    ct, th = solve_thumb(Y, hand)
    return c + THUMB_W * ct, hand, fing, th


def start_prm(Y, tilt):
    """Начальное положение кисти при наклоне tilt: костяшки — за телефоном у левого ребра."""
    h = Hand(Y, tilt, 0.0, 0.0, (0.0, 0.0, 0.0))
    k = h.pt((0.085, 0.0, 0.0))
    o = np.array((-14.0, 2.0, PH_Z0 - 11.0)) - k
    return [tilt, 0.0, 0.0] + [round(float(x), 1) for x in o]


SEEDS = [[24.0, -9.0, 24.0, 47.1, -76.6, -16.4], [24.0, -9.0, 24.0, 47.1, -76.6, -14.4]]   # прошлые хорошие решения — тоже старты (спуск локальный)


def solve_multi(Y, tilts=(0, 10, 20, 30, 40), iters=2):
    """Несколько стартов по наклону кисти и прошлые решения — берём лучший и уточняем."""
    best = None
    for st in [start_prm(Y, t) for t in tilts] + [list(x) for x in SEEDS]:
        prm, res = solve(Y, st, iters)
        if best is None or res[0] < best[1][0]:
            best = (prm, res)
    return solve(Y, best[0], 2)


def solve(Y, prm=None, iters=3):
    """Координатный спуск по положению кисти (наклон, тангаж, крен, u, v, w) с полным перебором пальцев внутри."""
    prm = list(prm or (35.0, 0.0, 0.0, 55.0, -40.0, -22.0))
    steps = [8.0, 6.0, 6.0, 8.0, 8.0, 4.0]
    best = total(Y, prm)[0]
    for it in range(iters):
        for k in range(len(prm)):
            for sgn in (1, -1):
                while True:
                    trial = list(prm); trial[k] += sgn * steps[k]
                    c = total(Y, trial)[0]
                    if c < best - 1e-6:
                        best, prm = c, trial
                    else:
                        break
        steps = [s / 2 for s in steps]
    return prm, total(Y, prm, fine=True)


# ----------------------------------------------------------------------------- сцена и экспорт
def _empty(sc, name, parent=None, size=0.01):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_size = size
    sc.collection.objects.link(ob)
    if parent:
        ob.parent = parent
    return ob


def setup_scene():
    src = bpy.data.scenes.get(SRC_SCENE)
    if src is None or "Yurchik3" not in src.objects:
        raise RuntimeError("нет сцены Yurchik3 — сначала соберите tools/blender/build_yurchik_v3.py")
    sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    if bpy.context.window:                                    # позы костей считаются в активной сцене окна
        bpy.context.window.scene = sc
    sun_d = bpy.data.lights.get("PoseSun") or bpy.data.lights.new("PoseSun", 'SUN')
    sun_d.energy = 2.5
    sun = bpy.data.objects.new("PoseSun", sun_d); sc.collection.objects.link(sun)
    sun.rotation_euler = Vector((0.3, 0.9, -0.6)).to_track_quat('-Z', 'Y').to_euler()
    cd = bpy.data.cameras.get("PoseCam") or bpy.data.cameras.new("PoseCam")
    cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(CAM_FOV); cd.clip_start = 0.01
    cam = bpy.data.objects.new("PoseCam", cd); sc.collection.objects.link(cam)
    cam.matrix_world = cam_matrix(); sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = RES
    root = _empty(sc, "PhoneRoot", None, 0.02)
    root.matrix_world = cam_matrix() @ phone_local()
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=PHONE_GLTF)
    fix = Matrix.Rotation(math.radians(-90), 4, 'X')        # импорт glTF: (u, v, w) → (u, −w, v); возвращаем оси модели
    for o in [o for o in bpy.data.objects if o not in before]:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        sc.collection.objects.link(o)
        o.name = "Phone_" + o.name
        if o.parent is None:
            mb = o.matrix_basis.copy()
            o.parent = root; o.matrix_parent_inverse = Matrix.Identity(4)
            o.matrix_basis = fix @ mb
    arm = src.objects["Yurchik3"].copy(); arm.name = "PoseRig"; sc.collection.objects.link(arm)
    body = src.objects["Yurchik3Mesh"].copy(); body.name = "PoseMesh"; sc.collection.objects.link(body)
    body.parent = arm
    for m in body.modifiers:
        if m.type == 'ARMATURE':
            m.object = arm
    if "Head" in body.vertex_groups:                         # голова не заслоняет камеру
        mk = body.modifiers.new("HideHead", 'MASK'); mk.vertex_group = "Head"; mk.invert_vertex_group = True
    for b in arm.pose.bones:
        b.rotation_mode = 'QUATERNION'; b.rotation_quaternion = (1, 0, 0, 0); b.location = (0, 0, 0); b.scale = (1, 1, 1)
        for c in list(b.constraints):
            b.constraints.remove(c)
    w = bpy.data.worlds.get("PoseWorld") or bpy.data.worlds.new("PoseWorld")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.35, 0.36, 0.38, 1.0); bg.inputs[1].default_value = 0.8
    sc.world = w
    return sc, arm, root


def apply_pose(Y, sc, arm, root, hand, fing, th):
    """Кость кисти — подобие «кисть в покое → кисть у телефона»; пальцы — наведение костей на суставы."""
    scale = hand_scale()
    P2A = phone_to_arm()
    rest_o = Y["mx"](Y["HAND_W"], -1)
    Rr = Matrix((Y["mx"](Y["HAND_L"], -1), Y["mx"](Y["HAND_WD"], -1), Y["mx"](Y["HAND_PN"], -1))).transposed()
    r3 = P2A.to_3x3().normalized()
    Rp = Matrix((r3 @ Vector(hand.L), r3 @ Vector(hand.W), r3 @ Vector(hand.P))).transposed()
    R = Rp @ Rr.inverted()
    assert abs(R.determinant() - 1.0) < 1e-3, "оси кисти и покоя разной ориентации"
    o_p = P2A @ Vector(hand.o)
    Phi = Matrix.Translation(o_p) @ R.to_4x4() @ Matrix.Scale(scale, 4) @ Matrix.Translation(-rest_o)
    pb = arm.pose.bones
    # плечо и предплечье — двухзвенный IK в игре; здесь — тот же IK-констрейнт для картинки
    goal = _empty(sc, "HandGoal", None, 0.02)
    goal.matrix_world = arm.matrix_world @ Phi @ arm.data.bones["HandR"].matrix_local
    ct = pb["HandR"].constraints.new('COPY_TRANSFORMS'); ct.target = goal
    ik = pb["ForearmR"].constraints.new('IK'); ik.target = goal; ik.chain_count = 2; ik.use_tail = False
    pole = _empty(sc, "ElbowPole", None, 0.05)
    pole.location = arm.data.bones["UpperArmR"].head_local + g2b((-0.6, -1.0, -0.15)).normalized() * 0.5
    ik.pole_target = pole; ik.pole_angle = math.radians(-90)
    sc.view_layers[0].update()

    def to_arm_mm(x):
        return arm.matrix_world.inverted() @ (P2A @ Vector(x))

    joints = {}
    for n in FINGERS[:4]:
        joints[n] = [hand.pt(p) for p in finger_fk(Y, n, *(np.array(a) for a in fing[n]))]
    joints["Thumb"] = list(th)
    for k in (1, 2, 3):
        sc.view_layers[0].update()
        for n in FINGERS:
            b = pb[f"{n}R{k}"]
            loc, rot, scl = b.matrix.decompose()
            cur = (rot @ Vector((0, 1, 0))).normalized()
            want = (to_arm_mm(joints[n][k]) - b.head).normalized()
            b.matrix = Matrix.LocRotScale(loc, cur.rotation_difference(want) @ rot, scl)
    sc.view_layers[0].update()
    return joints


def save_pose(sc, arm, root, path=POSE_JSON, extra=None):
    sc.view_layers[0].update()
    rinv = root.matrix_world.inverted()
    bones = {}
    for n in POSE_BONES:
        m = rinv @ arm.matrix_world @ arm.pose.bones[n].matrix
        q = m.to_quaternion().normalized()
        bones[n] = [round(q.x, 6), round(q.y, 6), round(q.z, 6), round(q.w, 6)]
    o = (rinv @ arm.matrix_world @ arm.pose.bones["HandR"].matrix).translation
    hs = (arm.pose.bones["HandR"].matrix.to_scale()[0])
    data = {"about": "Поза правой кисти с телефоном (tools/blender/pose_phone_hold.py, решается автоматически). "
                     "Повороты костей — кватернионы [x, y, z, w] в осях узла Phone в Godot, origin — начало кости HandR "
                     "в тех же осях (без масштаба телефона), hand_scale — масштаб кисти (HAND_SCALE в phone.gd).",
            "hand_scale": round(hs, 4), "origin": [round(o.x, 6), round(o.y, 6), round(o.z, 6)], "bones": bones}
    if extra:
        data["solver"] = extra
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def occlusion(sc, arm, root, n=12):
    """Сколько лучей из камеры в сетку точек экрана упирается в кисть (должно быть 0)."""
    dg = bpy.context.evaluated_depsgraph_get()
    body = sc.objects["PoseMesh"].evaluated_get(dg)
    me = body.to_mesh()
    import mathutils.bvhtree as bvh
    mw = body.matrix_world
    tree = bvh.BVHTree.FromPolygons([mw @ v.co for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    body.to_mesh_clear()
    cam = sc.camera.matrix_world.translation
    P2A = phone_to_arm()
    hits = 0
    for u in np.linspace(SCREEN[0] + 1, SCREEN[1] - 1, n):
        for v in np.linspace(SCREEN[2] + 1, SCREEN[3] - 1, n):
            pt = arm.matrix_world @ (P2A @ Vector((u, v, 6.1)))
            d = pt - cam
            loc, *_ = tree.ray_cast(cam, d.normalized(), d.length - 0.0005)
            hits += loc is not None
    return hits


def render(sc, path):
    sc.render.engine = 'BLENDER_EEVEE'
    sc.view_settings.view_transform = 'Standard'
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True, scene=sc.name)
    return path


def run(render_path=None, prm=None):
    """Решить позу (prm — готовое положение кисти, тогда только уточнить), построить сцену, записать JSON."""
    Y = _build_ns()
    prm, (cost, hand, fing, th) = solve(Y, prm, 1) if prm else solve_multi(Y)
    sc, arm, root = setup_scene()
    joints = apply_pose(Y, sc, arm, root, hand, fing, th)
    occ = occlusion(sc, arm, root)
    pads = {n: [round(float(x), 1) for x in (joints[n][2] + (joints[n][3] - joints[n][2]) * 0.6)] for n in FINGERS}
    extra = {"hand": [round(x, 2) for x in prm], "cost": round(cost, 3), "screen_hits": occ,
             "fingers_deg": {n: [round(math.degrees(a), 1) for a in v] for n, v in fing.items()},
             "thumb_mm": [[round(float(x), 1) for x in p] for p in th], "pads_mm": pads}
    save_pose(sc, arm, root, extra=extra)
    if render_path:
        render(sc, render_path)
    return extra
