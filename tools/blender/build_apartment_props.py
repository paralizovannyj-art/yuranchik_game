# -*- coding: utf-8 -*-
# Квартира 47, шаг 2: двери и мебель прихожей и коридора — по тем же двум фото, что и оболочка
# (docs/references/apartment/hall_1_to_room.webp, hall_2_to_entrance.webp; оболочка — build_apartment.py).
#
# Каждая вещь — отдельная low-poly модель (PS2): assets/models/apartment/<вещь>.gltf, позиции — в общем layout.json.
#   entry_door_in   — входная дверь изнутри: тёмно-коричневая, глазок, замок, ручка (в Godot — дочерняя к AptDoor
#                     подъезда и поворачивается вместе с ней);
#   double_door     — двустворчатая дверь в зал с янтарным рифлёным стеклом (южная стена прихожей);
#   door_wc         — узкая белая дверь у входа; door_white_a / door_white_b — белые филёнчатые двери по коридору
#                     (одна с круглой деревянной ручкой). Все — закрытый декор, за ними пока ничего нет;
#   wardrobe        — бежевый шкаф-купе почти до потолка; shelf — открытая полочка с обувью; desk_lamp — жёлтая лампа;
#   painting, poster — абстрактная картина (синий, красный, чёрная «роза») и постер с собакой над полочкой;
#   mop_sticks, bags_shoes, plastic_bag — палки от швабры, гора пакетов и обуви, белый пакет у шкафа;
#   nightstand, vase_flowers, mug — чёрная тумбочка в коридоре, на ней ваза с сухоцветами и кружка;
#   sconce, switch_entry, switch_corridor — бра над входной дверью и выключатели;
#   hooks_umbrella  — крючки с чёрным зонтом и плетёной сумочкой; vacuum, basket — пылесос и плетёная корзина.
# С коллизией только шкаф, полочка и тумбочка (имя без _nocol); мелочь и двери-декор — без (за дверями глухая
# стенка оболочки, она и держит игрока).
#
# Запуск — только через Blender MCP (живой Blender), строит в своей сцене «ApartmentProps»:
#   exec(open(r"<корень>/tools/blender/build_apartment_props.py", encoding="utf-8").read(),
#        {"__file__": r"<корень>/tools/blender/build_apartment_props.py", "__name__": "__main__"})
# Координаты — как в build_apartment.py (Blender, Z вверх, пол квартиры z = 8.4).
import bpy, os, sys, math, json
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
_sh = {"__file__": os.path.join(HERE, "build_apartment.py"), "__name__": "ap_shell"}
exec(compile(open(os.path.join(HERE, "build_apartment.py"), encoding="utf-8").read(), "build_apartment.py", "exec"), _sh)
globals().update({k: _sh[k] for k in (
    "B", "mat", "save", "C", "finish", "noise", "smoothstep", "mottle", "blur", "Items", "export_items", "RT",
    "Z", "H", "ZT", "HX0", "HX1", "HY0", "HY1", "CX0", "CX1", "CY0", "PX1", "PY1", "T", "DH",
    "ENTRY", "DOUBLE_DOOR", "WC_DOOR", "WEST_DOORS", "RUNNER", "PT", "EXT", "X_CUT")})

# вещи, заданные числами по старой (короткой) прихожей и стоящие западнее X_CUT: при экспорте сдвигаются на EXT к −x
# (то, что задано через HX0 / DOUBLE_DOOR / … — уже сдвинуто в build_apartment.py)
SHIFT_WEST = ("wardrobe", "shelf", "desk_lamp", "painting", "poster", "mop_sticks", "bags_shoes", "vacuum", "basket")

DOOR_X_IN = -3.05            # внутренняя грань входной двери (AptDoor в build_mvp_assets.py: x −3.05…−3.0, петли y = 0.8)


# =====================================================================================
#  Текстуры
# =====================================================================================
def _grid(h, w):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return yy, xx


def _bevel(arr, mask, d=2, dark=0.72, light=1.10):
    """Утопленная филёнка: тень сверху-слева, свет снизу-справа, вокруг — тонкий штапик."""
    top = mask & ~np.roll(mask, d, 0); left = mask & ~np.roll(mask, d, 1)
    bot = mask & ~np.roll(mask, -d, 0); right = mask & ~np.roll(mask, -d, 1)
    ring = (np.roll(mask, 2, 0) | np.roll(mask, -2, 0) | np.roll(mask, 2, 1) | np.roll(mask, -2, 1)) & ~mask
    arr[mask] *= 0.95
    arr[top | left] *= dark
    arr[bot | right] *= light
    arr[ring] *= 1.06
    ring2 = (np.roll(ring, 1, 0) | np.roll(ring, 1, 1)) & ~ring & ~mask
    arr[ring2] *= 0.85


def _paint(w, h, rng, base):
    """Крашеное дерево — фото CC0 ambientCG PaintedWood009C (мазки кисти, сколы), приведённое к тону base;
    свой кусок для каждой створки."""
    src = PT.flatten(PT.lib("ambientcg/PaintedWood009C"), 80)
    sw, sh = min(2 * w, src.shape[1]), min(2 * h, src.shape[0])                       # кусок фото в 2 раза крупнее
    x0, y0 = int(rng.integers(0, src.shape[1] - sw + 1)), int(rng.integers(0, src.shape[0] - sh + 1))
    a = PT.resize(src[y0:y0 + sh, x0:x0 + sw], w, h)
    return PT.recolor(a, base, contrast=0.7)


def _dirt(arr, rng, hu, hv):
    """Засаленное пятно у ручки (u, v — доли ширины и высоты, v от верха) и пыль внизу."""
    h, w, _ = arr.shape
    yy, xx = _grid(h, w); u, v = xx / w, yy / h
    g = np.clip(1 - np.sqrt(((u - hu) / 0.18) ** 2 + ((v - hv) / 0.07) ** 2), 0, 1) ** 1.5
    arr *= (1 - 0.28 * g)[..., None]
    low = np.clip((v - 0.88) / 0.12, 0, 1) ** 1.3
    arr *= (1 - 0.25 * low * (0.5 + 0.5 * noise(w, h, 10, 4, rng, oct=3)))[..., None]


def tex_door_white():
    """Белая филёнчатая дверь (фото 1, справа): сверху высокая филёнка с выпуклой аркой, снизу — прямоугольная.
    Ручка справа (u ≈ 0.9). 0.8 x 2.05 м, 128 x 256."""
    rng = np.random.default_rng(4711)
    w, h = 128, 256
    arr = _paint(w, h, rng, (0.86, 0.85, 0.80))
    yy, xx = _grid(h, w); u, v = xx / w, yy / h
    top = 0.075 + 0.05 * ((u - 0.5) / 0.33) ** 2
    up = (u > 0.17) & (u < 0.83) & (v > top) & (v < 0.52)
    lo = (u > 0.17) & (u < 0.83) & (v > 0.57) & (v < 0.92)
    for m_ in (up, lo):
        _bevel(arr, m_)
    _dirt(arr, rng, 0.9, 0.52)
    save("ap_door_white", finish(arr, 1.0, crisp=0.25))


def tex_door_glass():
    """Створки двустворчатой двери в зал (фото 1, слева): кремово-белая краска, сверху рифлёное «пупырчатое»
    стекло, снизу филёнка. Слева в текстуре — створка с медово-янтарным стеклом (за ним светло), справа — с
    тёмно-коричневым (за ним темно). Каждая 0.6 x 2.05 м, 64 x 256; вся текстура 128 x 256."""
    rng = np.random.default_rng(4712)
    w, h = 64, 256
    # рифлёное янтарное стекло — с фото 1 (левая створка двустворчатой двери), без света с улицы
    glass_photo = PT.flatten(PT.rectify(PT.load("hall_1_to_room.webp"), [(178, 730), (262, 735), (262, 1040), (190, 1040)],
                                        40, 150, ss=3), 10)
    leaves = []
    for glass, bright in ((C(0.86, 0.54, 0.14), 0.30), (C(0.30, 0.17, 0.09), 0.12)):
        arr = _paint(w, h, rng, (0.87, 0.86, 0.80))
        yy, xx = _grid(h, w); u, v = xx / w, yy / h
        gl = (u > 0.16) & (u < 0.84) & (v > 0.07) & (v < 0.60)
        g = PT.resize(glass_photo, w, h) * (glass / glass_photo.reshape(-1, 3).mean(0))
        g *= (1 - bright + bright * 2 * smoothstep(0.62, 0.05, v))[..., None]            # сверху светлее
        arr[gl] = g[gl]
        _bevel(arr, gl, d=1, dark=0.7, light=1.15)
        lo = (u > 0.16) & (u < 0.84) & (v > 0.66) & (v < 0.93)
        _bevel(arr, lo)
        _dirt(arr, rng, 0.85, 0.52)
        leaves.append(arr)
    save("ap_door_glass", finish(np.concatenate(leaves, 1), 1.0, crisp=0.2))


def tex_entry_in():
    """Входная дверь изнутри — с фото 2 (выпрямлена): гладкая, тёмно-коричневая с бордовым;
    глазок на 1.5 м, у замка (u ≈ 0.1) — скважина, низ затёрт. 0.9 x 2.05 м, 64 x 128."""
    rng = np.random.default_rng(4713)
    w, h = 64, 128
    photo = PT.flatten(PT.rectify(PT.load("hall_2_to_entrance.webp"), [(706, 666), (824, 664), (821, 1006), (709, 1008)],
                                  w, h, ss=4), 20)                                     # дверь с фото 2
    arr = PT.recolor(photo, (0.27, 0.10, 0.085), contrast=1.6, chroma=0.3)
    yy, xx = _grid(h, w); u, v = xx / w, yy / h
    edge = np.minimum(np.minimum(u, 1 - u) * 9, np.minimum(v, 1 - v) * 20)
    arr *= (0.75 + 0.25 * np.clip(edge, 0, 1))[..., None]
    pu, pv = 0.5 * w, (2.05 - 1.55) / 2.05 * h                                             # глазок
    r = np.hypot(xx + 0.5 - pu, yy + 0.5 - pv)
    arr[r < 2.6] = C(0.62, 0.50, 0.28)
    arr[r < 1.2] = C(0.02, 0.02, 0.03)
    ku, kv = 0.1 * w, (2.05 - 1.25) / 2.05 * h                                             # скважина верхнего замка
    arr[(np.abs(xx + 0.5 - ku) < 1.6) & (np.abs(yy + 0.5 - kv) < 2.6)] = C(0.55, 0.45, 0.25)
    arr[(np.abs(xx + 0.5 - ku) < 0.6) & (np.abs(yy + 0.5 - kv) < 1.6)] = C(0.03, 0.03, 0.03)
    _dirt(arr, rng, 0.1, 0.5)
    arr *= mottle(h, w, rng, 2, 0.1)[..., None]
    save("ap_entry_in", finish(arr, 1.0, crisp=0.3))


def tex_wardrobe():
    """Створка шкафа-купе (фото 2): бежевый ламинат «под клён» (CC0 Poly Haven white_maple_veneer), по краям — вертикальный
    профиль цвета шампань, сверху и снизу — рельсы. 0.87 x 2.4 м, 128 x 256."""
    rng = np.random.default_rng(4714)
    w, h = 128, 256
    ven = np.rot90(PT.flatten(PT.lib("polyhaven/white_maple_veneer"), 60))           # волокна вдоль створки
    arr = PT.recolor(PT.resize(ven[:, :400], w, h), (0.84, 0.76, 0.62), contrast=1.1, chroma=0.3)
    yy, xx = _grid(h, w); u, v = xx / w, yy / h
    arr *= (0.93 + 0.1 * smoothstep(0.0, 0.5, u) * smoothstep(1.0, 0.5, u))[..., None]   # блик по середине
    prof = (u < 0.04) | (u > 0.96)
    arr[prof] = C(0.58, 0.52, 0.40) * (0.85 + 0.3 * np.abs(np.sin(xx * 1.4)))[prof][..., None]
    rail = (v < 0.018) | (v > 0.975)
    arr[rail] = C(0.45, 0.40, 0.31)
    g = np.clip(1 - np.sqrt(((u - 0.08) / 0.12) ** 2 + ((v - 0.45) / 0.12) ** 2), 0, 1)  # захватанный край
    arr *= (1 - 0.12 * g)[..., None]
    save("ap_wardrobe", finish(arr, 1.0, crisp=0.25))


def tex_glow():
    """Тёплое матовое стекло бра (светится)."""
    a = np.ones((16, 16, 3), np.float32) * C(1.0, 0.86, 0.62)
    yy, xx = _grid(16, 16)
    a *= (0.85 + 0.15 * (yy / 16))[..., None]
    save("ap_glow", a)


# атлас мелочи 256 x 256: (x0, y0, x1, y1) в пикселях от левого верхнего угла
P = {
    "painting": (0, 0, 64, 88), "poster": (64, 0, 128, 88),
    "yellow": (128, 0, 160, 16), "teal": (160, 0, 192, 16), "lacquer": (192, 0, 256, 16),
    "wicker": (128, 16, 192, 48), "vac": (192, 16, 224, 32), "hose": (224, 16, 256, 32),
    "pine": (192, 32, 224, 48), "melamine": (224, 32, 256, 48),
    "cream": (128, 48, 192, 64), "brass": (192, 48, 224, 64), "metal": (224, 48, 256, 64),
    "bags": (128, 64, 256, 112), "shoes": (0, 88, 64, 112), "sneakers": (64, 88, 128, 112),
    "vase": (0, 112, 64, 144), "mug": (64, 112, 128, 144), "flowers": (128, 112, 192, 144),
    "switch": (192, 112, 224, 144), "umbrella": (224, 112, 256, 144),
    "cloth": (0, 144, 64, 176), "red": (64, 144, 96, 176), "white": (96, 144, 128, 176),
    "jacket": (128, 144, 192, 176), "sack": (192, 144, 256, 176), "black": (0, 176, 64, 208),
}


def tex_props():
    rng = np.random.default_rng(4715)
    A = np.zeros((256, 256, 3), np.float32)

    def reg(name):
        x0, y0, x1, y1 = P[name]
        return A[y0:y1, x0:x1], y1 - y0, x1 - x0

    def fill(name, col, var=0.1, cx=4, cy=4):
        a, h, w = reg(name)
        a[:] = C(*col) * (1 - var + 2 * var * noise(w, h, cx, cy, rng, oct=2))[..., None]
        return a, h, w

    # картина: чёрная рамка, белое паспарту, 2 x 2: синий, синий, красный, белый; чёрные «розы»-завитки
    a, h, w = reg("painting")
    yy, xx = _grid(h, w)
    a[:] = C(0.04, 0.04, 0.04)
    a[3:-3, 3:-3] = C(0.88, 0.87, 0.84)
    x0, x1, y0, y1, xm, ym = 8, w - 8, 8, h - 8, w // 2, h // 2
    a[y0:ym, x0:xm] = C(0.12, 0.26, 0.66); a[y0:ym, xm:x1] = C(0.10, 0.24, 0.62)
    a[ym:y1, x0:xm] = C(0.78, 0.12, 0.10); a[ym:y1, xm:x1] = C(0.90, 0.88, 0.85)
    for (cx, cy, rr) in ((xm - 6, ym - 10, 13), (xm + 8, ym + 14, 14)):
        r = np.hypot(xx - cx, yy - cy); th = np.arctan2(yy - cy, xx - cx)
        swirl = (np.abs(np.sin(r * 0.55 + th * 1.0)) < 0.38) & (r < rr)
        a[swirl] = C(0.03, 0.03, 0.03)
    a[(np.abs(xx - xm) < 2) & (yy > y0 + 6) & (yy < y1 - 6) & (np.abs(np.sin(yy * 0.3)) < 0.6)] = C(0.03, 0.03, 0.03)
    # постер: тёмно-синий фон, светло-серая морда собаки, тёмные глаза и нос
    a, h, w = reg("poster")
    yy, xx = _grid(h, w)
    a[:] = C(0.05, 0.07, 0.14) * (0.7 + 0.5 * smoothstep(h, 0, yy))[..., None]
    head = ((xx - 32) / 15) ** 2 + ((yy - 44) / 19) ** 2 < 1
    ears = (((xx - 21) / 6) ** 2 + ((yy - 24) / 12) ** 2 < 1) | (((xx - 43) / 6) ** 2 + ((yy - 24) / 12) ** 2 < 1)
    dog = head | ears
    a[dog] = (C(0.72, 0.70, 0.66) * (0.75 + 0.35 * noise(w, h, 8, 8, rng, oct=2))[..., None])[dog]
    for ex in (26, 38):
        a[((xx - ex) ** 2 + (yy - 40) ** 2) < 5] = C(0.03, 0.03, 0.03)
    a[((xx - 32) / 3.5) ** 2 + ((yy - 54) / 2.5) ** 2 < 1] = C(0.04, 0.03, 0.03)
    a[3:6, 6:w - 6] = C(0.6, 0.6, 0.55); a[h - 9:h - 6, 10:w - 10] = C(0.5, 0.5, 0.45)
    fill("yellow", (0.95, 0.74, 0.10), 0.05)
    fill("teal", (0.06, 0.24, 0.30), 0.1)
    a, h, w = fill("lacquer", (0.06, 0.055, 0.05), 0.15)
    a[noise(w, h, 20, 6, rng, oct=2) > 0.75] *= 2.2                                       # царапины лака
    # плетёнка: косое переплетение
    a, h, w = reg("wicker")
    yy, xx = _grid(h, w)
    s1 = np.sin((xx + yy) * 0.9); s2 = np.sin((xx - yy) * 0.9)
    weave = np.where(((xx + yy) // 4 + (xx - yy) // 4) % 2 == 0, s1, s2)
    a[:] = C(0.55, 0.40, 0.22) * (0.65 + 0.35 * np.abs(weave))[..., None]
    fill("vac", (0.12, 0.12, 0.13), 0.12)
    a, h, w = fill("hose", (0.05, 0.05, 0.05), 0.1)
    a[::3] *= 2.0                                                                         # гофра шланга
    a, h, w = fill("pine", (0.78, 0.60, 0.38), 0.1, 2, 8)
    fill("melamine", (0.86, 0.83, 0.75), 0.05)
    fill("cream", (0.84, 0.77, 0.63), 0.05)
    a, h, w = fill("brass", (0.66, 0.50, 0.26), 0.15)
    a[: h // 3] *= 1.3
    fill("metal", (0.20, 0.19, 0.18), 0.15)
    # гора пакетов: бежевый мешок, тёмная куртка, белые и красные пакеты, складки
    a, h, w = reg("bags")
    n = noise(w, h, 6, 4, rng, oct=3)
    cols = [C(0.70, 0.62, 0.48), C(0.12, 0.12, 0.14), C(0.85, 0.84, 0.80), C(0.55, 0.14, 0.12), C(0.30, 0.32, 0.36)]
    idx = np.clip((n * 5).astype(int), 0, 4)
    a[:] = np.stack(cols)[idx] * (0.65 + 0.45 * noise(w, h, 18, 10, rng, oct=2))[..., None]
    a, h, w = fill("shoes", (0.09, 0.08, 0.07), 0.15)
    a[h - 5:] = C(0.15, 0.13, 0.11)
    a, h, w = fill("sneakers", (0.84, 0.84, 0.82), 0.06)
    a[h - 6:] = C(0.45, 0.45, 0.44); a[4:7, :] = C(0.20, 0.30, 0.55)
    # ваза: белый фарфор с синим цветочным узором
    a, h, w = fill("vase", (0.86, 0.87, 0.88), 0.04)
    yy, xx = _grid(h, w)
    a[np.abs(np.sin(xx * 0.4) * 5 + 16 - yy) < 1.6] = C(0.12, 0.20, 0.55)
    a[((xx % 16 - 8) ** 2 + (yy - 8) ** 2) < 7] = C(0.15, 0.25, 0.60)
    a[(np.abs(yy - 27) < 2)] = C(0.12, 0.20, 0.55)
    a, h, w = fill("mug", (0.88, 0.88, 0.86), 0.04)
    a[12:24] = C(0.10, 0.28, 0.45)
    a, h, w = fill("flowers", (0.70, 0.58, 0.38), 0.25, 10, 10)
    a[noise(w, h, 14, 14, rng, oct=2) > 0.62] = C(0.86, 0.80, 0.62)
    a, h, w = fill("switch", (0.86, 0.82, 0.70), 0.04)
    a[:, w // 2] *= 0.75; a[2:4] *= 1.1; a[-3:] *= 0.8
    a, h, w = fill("umbrella", (0.05, 0.05, 0.06), 0.1)
    a[:, ::6] *= 2.0                                                                      # складки
    a, h, w = fill("cloth", (0.38, 0.39, 0.38), 0.25, 6, 6)
    fill("red", (0.52, 0.12, 0.10), 0.12)
    fill("white", (0.88, 0.88, 0.86), 0.06)
    a, h, w = fill("jacket", (0.10, 0.11, 0.13), 0.25, 6, 4)
    a, h, w = fill("sack", (0.72, 0.64, 0.50), 0.2, 6, 5)
    fill("black", (0.03, 0.03, 0.035), 0.1)
    # фотобашинг: материалы мелочи — куски фото прихожей (картина и постер остаются нарисованными)
    h1, h2 = PT.load("hall_1_to_room.webp"), PT.load("hall_2_to_entrance.webp")
    for name, img, box, k in (
            ("wicker", h1, (380, 1350, 540, 1420), 1.0),       # плетёная корзина
            ("lacquer", h1, (905, 1440, 1085, 1600), 1.0),     # чёрная тумбочка
            ("bags", h2, (170, 1450, 440, 1720), 1.0),         # гора пакетов и одежды
            ("jacket", h2, (190, 1700, 330, 1880), 1.0),       # тёмная куртка
            ("vac", h2, (950, 1390, 1040, 1500), 1.0),         # пылесос
            ("cloth", h1, (410, 1395, 540, 1480), 1.0),        # тряпка в корзине
            ("flowers", h1, (1045, 1150, 1110, 1250), 1.0),    # сухие цветы
            ("mug", h1, (1028, 1305, 1080, 1385), 1.0),        # кружка
            ("switch", h1, (1176, 962, 1200, 1022), 1.0),      # выключатель
            ("umbrella", h2, (905, 760, 945, 900), 1.0),       # зонт на крючке
            ("shoes", h1, (30, 1870, 150, 1990), 1.0)):        # обувь
        x0, y0, x1, y1 = P[name]
        a = PT.flatten(PT.crop(img, *box), max(4, (box[2] - box[0]) / 3), strength=0.6)
        A[y0:y1, x0:x1] = np.clip(PT.resize(a, x1 - x0, y1 - y0) * k, 0, 1)
    save("ap_props", finish(A, 1.0, crisp=0.3))


# =====================================================================================
#  Геометрия: помощники
# =====================================================================================
def RA(name, flip=False):
    x0, y0, x1, y1 = P[name]
    u0, v0, u1, v1 = (x0 + 0.5) / 256, 1 - (y1 - 0.5) / 256, (x1 - 0.5) / 256, 1 - (y0 + 0.5) / 256
    return (u1, v0, u0, v1) if flip else (u0, v0, u1, v1)


def PR(name):
    return (M["props"], RA(name))


ALL = ('+X', '-X', '+Y', '-Y', '+Z', '-Z')


def cube(b, mn, mx, fm, skip=('-Z',)):
    b.box(mn, mx, {k: fm for k in ALL if k not in skip})


def cyl(b, p0, p1, r0, r1, fm, segs=6, caps=False):
    """Цилиндр/конус с UV в прямоугольнике атласа."""
    m, (u0, v0, u1, v1) = fm
    n0 = len(b.uv)
    L = max((Vector(p1) - Vector(p0)).length, 1e-4)
    b.cyl(p0, p1, r0, r1, m, segs=segs, caps=caps, su=L)
    for i in range(n0, len(b.uv)):
        b.uv[i] = [(u0 + min(max(u, 0), 1) * (u1 - u0), v0 + min(max(v, 0), 1) * (v1 - v0)) for (u, v) in b.uv[i]]


def lathe(b, cx, cy, prof, fm, segs=8, cap=False, inside=False):
    """Тело вращения: prof — [(радиус, z), ...] снизу вверх."""
    n0 = len(b.f)
    for (r0, z0), (r1, z1) in zip(prof, prof[1:]):
        cyl(b, (cx, cy, z0), (cx, cy, z1), r0, r1, fm, segs=segs)
    if cap:
        cyl(b, (cx, cy, prof[-1][1]), (cx, cy, prof[-1][1] + 1e-3), prof[-1][0], prof[-1][0], fm, segs=segs, caps=True)
    if inside:
        flip(b, n0)


def flip(b, n0):
    """Добавить вывернутые копии граней n0… (видно и изнутри)."""
    for i in range(n0, len(b.f)):
        pts = [Vector(b.v[j]) for j in b.f[i]][::-1]
        b.poly(pts, b.uv[i][::-1], b.mats[b.mi[i]])


def blind_door(b, axis, c, n, a, bb, leaves, white, knobs=(), handles=(), cornice=False):
    """Закрытая дверь-декор в глухом проёме оболочки: створки утоплены на 4 см, вокруг на стене — белый наличник.
    axis 'x' — стена x = c (вдоль y), 'y' — стена y = c (вдоль x); n — куда смотрит лицо стены.
    leaves — [(начало, конец, (мат, rect))]; knobs — круглые ручки (s, z), handles — нажимные (s, z, ±1 — куда язык)."""
    key = ('+' if n > 0 else '-') + axis.upper()
    sk = 'Y' if axis == 'x' else 'X'

    def box(sa, sb, za, zb, d0, d1, faces):
        if axis == 'x':
            b.box((min(d0, d1), sa, za), (max(d0, d1), sb, zb), faces)
        else:
            b.box((sa, min(d0, d1), za), (sb, max(d0, d1), zb), faces)

    def pt(s, z, d):
        return (c + n * d, s, z) if axis == 'x' else (s, c + n * d, z)

    tr = (M["trim"], RT("white"))
    for (s0, s1, fm) in leaves:
        box(s0, s1, Z + 0.012, Z + DH - 0.004, c - n * 0.08, c - n * 0.04, {key: fm, '+' + sk: tr, '-' + sk: tr, '-Z': tr})
    w = 0.07
    cas = {key: tr, '+Z': tr, '-Z': tr, '+' + sk: tr, '-' + sk: tr}
    box(a - w, a, Z, Z + DH + w, c, c + n * 0.012, cas)
    box(bb, bb + w, Z, Z + DH + w, c, c + n * 0.012, cas)
    box(a, bb, Z + DH, Z + DH + w, c, c + n * 0.012, cas)
    if cornice:                                                              # карниз над наличником (дверь в зал)
        box(a - w - 0.03, bb + w + 0.03, Z + DH + w, Z + DH + w + 0.04, c, c + n * 0.035, cas)
    for (s, z) in knobs:                                                     # круглая деревянная ручка
        cyl(b, pt(s, z, -0.04), pt(s, z, 0.0), 0.012, 0.012, PR("brass"), segs=5)
        cyl(b, pt(s, z, 0.0), pt(s, z, 0.035), 0.016, 0.028, PR("pine"), segs=6)
        cyl(b, pt(s, z, 0.035), pt(s, z, 0.055), 0.028, 0.012, PR("pine"), segs=6, caps=True)
    for (s, z, dr) in handles:                                               # нажимная ручка: стержень и язык
        cyl(b, pt(s, z, -0.04), pt(s, z, 0.03), 0.008, 0.008, PR("brass"), segs=4)
        cyl(b, pt(s, z, 0.03), pt(s + dr * 0.11, z, 0.035), 0.009, 0.008, PR("brass"), segs=4, caps=True)
        box(s - 0.02, s + 0.02, z - 0.07, z + 0.05, c - n * 0.04, c - n * 0.035, {key: PR("brass")})


# =====================================================================================
#  Вещи
# =====================================================================================
def props():
    coll = bpy.context.scene.collection
    I = Items()
    tr_white = (M["trim"], RT("white"))

    # --- входная дверь изнутри: лицо поверх внутренней грани AptDoor, ручка, «барашек» замка ---
    e = I("entry_door_in", nocol=True)
    y0, y1 = ENTRY[0] + 0.003, ENTRY[1] - 0.003
    x = DOOR_X_IN
    e.box((x - 0.006, y0, Z + 0.003), (x, y1, Z + DH - 0.003), {'-X': (M["entry"], (0, 0, 1, 1))})
    hy, hz = ENTRY[1] - 0.10, Z + 1.0
    e.box((x - 0.016, hy - 0.025, hz - 0.10), (x - 0.006, hy + 0.025, hz + 0.08), {k: PR("brass") for k in ('-X', '+Y', '-Y', '+Z', '-Z')})
    cyl(e, (x - 0.016, hy, hz), (x - 0.06, hy, hz), 0.009, 0.009, PR("brass"), segs=4)
    cyl(e, (x - 0.06, hy + 0.005, hz), (x - 0.065, hy - 0.12, hz - 0.01), 0.011, 0.009, PR("brass"), segs=4, caps=True)
    cyl(e, (x - 0.006, hy, Z + 1.25), (x - 0.03, hy, Z + 1.25), 0.022, 0.022, PR("brass"), segs=6, caps=True)
    e.box((x - 0.045, hy - 0.004, Z + 1.23), (x - 0.03, hy + 0.004, Z + 1.27), {k: PR("brass") for k in ('-X', '+Y', '-Y', '+Z')})

    # --- двустворчатая дверь в зал (стена y = HY0), створки — стекло сверху ---
    a, bb = DOUBLE_DOOR
    mid = (a + bb) / 2
    dd = I("double_door", nocol=True)
    gl = M["door_glass"]
    blind_door(dd, 'y', HY0, +1, a, bb, [(a + 0.004, mid - 0.002, (gl, (0.5, 0, 0, 1))), (mid + 0.002, bb - 0.004, (gl, (1, 0, 0.5, 1)))],
               tr_white, cornice=True)
    # --- узкая белая дверь у входа ---
    a, bb = WC_DOOR
    wc = I("door_wc", nocol=True)
    blind_door(wc, 'y', HY0, +1, a, bb, [(a + 0.004, bb - 0.004, (M["door_white"], (1, 0, 0, 1)))], tr_white,
               handles=[(a + 0.07, Z + 0.95, +1)])
    # --- две белые филёнчатые двери в коридоре (стена x = HX0) ---
    (a1, b1), (a2, b2) = WEST_DOORS
    wa = I("door_white_a", nocol=True)
    blind_door(wa, 'x', HX0, +1, a1, b1, [(a1 + 0.004, b1 - 0.004, (M["door_white"], (1, 0, 0, 1)))], tr_white,
               knobs=[(a1 + 0.08, Z + 0.95)])
    wb = I("door_white_b", nocol=True)
    blind_door(wb, 'x', HX0, +1, a2, b2, [(a2 + 0.004, b2 - 0.004, (M["door_white"], (0, 0, 1, 1)))], tr_white,
               handles=[(b2 - 0.07, Z + 0.95, -1)])

    # --- шкаф-купе: корпус (с коллизией) и две створки внахлёст ---
    X0, X1, YF, YB, ZH = -5.70, -4.00, 1.72, HY1, Z + 2.45
    wr = I("wardrobe")
    cr, dk = PR("cream"), PR("metal")
    wr.box((X0, YF, Z), (X1, YB, ZH), {'+Z': cr, '-X': cr, '+X': cr, '-Y': dk})
    wrd = I("wardrobe", nocol=True)
    xm = (X0 + X1) / 2
    for (s0, s1, yf) in ((X0 + 0.015, xm + 0.03, YF - 0.025), (xm - 0.03, X1 - 0.015, YF - 0.012)):
        wrd.box((s0, yf, Z + 0.03), (s1, yf + 0.012, ZH - 0.03),
                {'-Y': (M["wardrobe"], (0, 0, 1, 1)), '-X': dk, '+X': dk, '+Z': dk})
    wrd.box((X0, YF - 0.03, ZH - 0.04), (X1, YF, ZH), {'-Y': dk, '-Z': dk})              # верхний рельс
    wrd.box((X0, YF - 0.03, Z), (X1, YF, Z + 0.03), {'-Y': dk, '+Z': dk})                # нижний

    # --- открытая полочка (с коллизией): боковины, полки, задник ---
    S0, S1, SF, ST = -6.20, -5.76, 1.86, Z + 0.95
    sh = I("shelf")
    mel = PR("melamine")
    t = 0.018
    cube(sh, (S0, SF, Z), (S0 + t, HY1, ST), mel)
    cube(sh, (S1 - t, SF, Z), (S1, HY1, ST), mel)
    for zz in (Z + 0.03, Z + 0.33, Z + 0.63, ST - t):
        cube(sh, (S0 + t, SF, zz), (S1 - t, HY1, zz + t), mel)
    sh.box((S0 + t, HY1 - 0.01, Z), (S1 - t, HY1, ST), {'-Y': mel})
    shd = I("shelf", nocol=True)                                             # обувь на полках
    for (zz, kind, xs) in ((Z + 0.048, "shoes", (-6.17, -5.98)), (Z + 0.348, "sneakers", (-6.16, -5.97)),
                           (Z + 0.648, "shoes", (-6.14, -5.95))):
        for k, x0_ in enumerate(xs):
            cube(shd, (x0_, SF + 0.02, zz), (x0_ + 0.16, SF + 0.30, zz + 0.09 - 0.02 * k), PR(kind))

    # --- жёлтая настольная лампа на полочке ---
    lp = I("desk_lamp", nocol=True)
    lx, ly = -5.90, 2.06
    lathe(lp, lx, ly, [(0.075, ST), (0.07, ST + 0.025), (0.03, ST + 0.035)], PR("yellow"), segs=8, cap=True)
    cyl(lp, (lx, ly, ST + 0.03), (lx + 0.02, ly - 0.04, ST + 0.30), 0.008, 0.008, PR("metal"), segs=4)
    hx, hy_, hz_ = lx + 0.03, ly - 0.10, ST + 0.30
    cyl(lp, (lx + 0.02, ly - 0.03, hz_ + 0.03), (hx, hy_, hz_ - 0.03), 0.025, 0.075, PR("yellow"), segs=8)
    n0 = len(lp.f)
    cyl(lp, (lx + 0.02, ly - 0.03, hz_ + 0.03), (hx, hy_, hz_ - 0.03), 0.022, 0.072, PR("teal"), segs=8)
    flip(lp, n0); del lp.f[n0:n0 + 8], lp.uv[n0:n0 + 8], lp.mi[n0:n0 + 8]                 # внутри абажура — тёмное

    # --- картина над полочкой и постер с собакой, прислонённый к стене ---
    pt = I("painting", nocol=True)
    pt.box((-6.62, HY1 - 0.025, Z + 1.30), (-6.12, HY1, Z + 1.98),
           {'-Y': PR("painting"), '-X': PR("black"), '+X': PR("black"), '-Z': PR("black"), '+Z': PR("black")})
    ps = I("poster", nocol=True)
    ps.poly([Vector((-6.15, HY1 - 0.09, ST + 0.002)), Vector((-5.83, HY1 - 0.09, ST + 0.002)),
             Vector((-5.83, HY1 - 0.01, ST + 0.47)), Vector((-6.15, HY1 - 0.01, ST + 0.47))],
            [(RA("poster")[0], RA("poster")[1]), (RA("poster")[2], RA("poster")[1]),
             (RA("poster")[2], RA("poster")[3]), (RA("poster")[0], RA("poster")[3])], M["props"])

    # --- палки от швабры: прислонены к углу шкафа ---
    ms = I("mop_sticks", nocol=True)
    cyl(ms, (-5.92, 1.76, Z), (-5.73, 2.15, Z + 2.02), 0.013, 0.013, PR("pine"), segs=5)
    cyl(ms, (-5.85, 1.80, Z), (-5.74, 2.17, Z + 1.72), 0.012, 0.012, PR("pine"), segs=5)

    # --- гора пакетов и обуви в углу у полочки ---
    bg = I("bags_shoes", nocol=True)
    lathe(bg, -6.46, 1.98, [(0.12, Z), (0.21, Z + 0.06), (0.22, Z + 0.26), (0.16, Z + 0.44), (0.05, Z + 0.50)],
          PR("sack"), segs=7, cap=True)
    bg.box((-6.60, 1.58, Z), (-6.30, 1.86, Z + 0.16), {k: PR("jacket") for k in ('+X', '-X', '+Y', '-Y', '+Z')})
    bg.box((-6.67, 1.62, Z + 0.16), (-6.42, 1.80, Z + 0.40), {k: PR("red") for k in ('+X', '-X', '+Y', '-Y', '+Z')})
    lathe(bg, -6.37, 1.72, [(0.09, Z + 0.16), (0.12, Z + 0.24), (0.08, Z + 0.36), (0.02, Z + 0.40)], PR("bags"), segs=6, cap=True)
    for (x0_, y0_) in ((-6.38, 1.50), (-6.35, 1.38)):
        cube(bg, (x0_, y0_, Z), (x0_ + 0.28, y0_ + 0.10, Z + 0.10), PR("shoes"))
    cube(bg, (-6.28, 1.66, Z), (-6.24, 1.95, Z + 0.09), PR("sneakers"))
    pb = I("plastic_bag", nocol=True)
    lathe(pb, -3.80, 1.96, [(0.10, Z), (0.16, Z + 0.08), (0.14, Z + 0.22), (0.06, Z + 0.30), (0.03, Z + 0.36)],
          PR("white"), segs=6, cap=True)

    # --- чёрная тумбочка в коридоре (с коллизией) ---
    N0, N1, NY0, NY1 = HX0 + 0.01, HX0 + 0.35, -0.86, -0.32
    ns = I("nightstand")
    lq = PR("lacquer")
    for (xa, ya) in ((N0 + 0.01, NY0 + 0.01), (N1 - 0.04, NY0 + 0.01), (N0 + 0.01, NY1 - 0.04), (N1 - 0.04, NY1 - 0.04)):
        cube(ns, (xa, ya, Z), (xa + 0.03, ya + 0.03, Z + 0.22), lq)
    cube(ns, (N0 + 0.01, NY0 + 0.01, Z + 0.07), (N1 - 0.01, NY1 - 0.01, Z + 0.09), lq)    # нижняя полочка
    cube(ns, (N0, NY0, Z + 0.22), (N1, NY1, Z + 0.58), lq, skip=())
    cube(ns, (N0, NY0 - 0.015, Z + 0.58), (N1 + 0.02, NY1 + 0.015, Z + 0.62), lq, skip=())
    nsd = I("nightstand", nocol=True)
    nsd.box((N1, NY0 + 0.03, Z + 0.25), (N1 + 0.003, NY1 - 0.03, Z + 0.55), {'+X': PR("black")})     # щель дверцы
    cyl(nsd, (N1, NY1 - 0.07, Z + 0.47), (N1 + 0.025, NY1 - 0.07, Z + 0.47), 0.01, 0.012, PR("brass"), segs=5, caps=True)
    TOP = Z + 0.62
    # --- на тумбочке: ваза с сухоцветами, кружка, пульт ---
    vs = I("vase_flowers", nocol=True)
    vx, vy = N0 + 0.12, NY1 - 0.08
    lathe(vs, vx, vy, [(0.035, TOP), (0.055, TOP + 0.06), (0.05, TOP + 0.14), (0.028, TOP + 0.19), (0.036, TOP + 0.22)],
          PR("vase"), segs=8)
    for k in range(7):
        ang = k * 2.4; r = 0.03 + 0.025 * (k % 3)
        tip = (vx + math.cos(ang) * r * 2.2, vy + math.sin(ang) * r * 2.2, TOP + 0.36 + 0.05 * (k % 3))
        cyl(vs, (vx, vy, TOP + 0.18), tip, 0.004, 0.003, PR("jacket"), segs=3)
        cube(vs, (tip[0] - 0.025, tip[1] - 0.025, tip[2] - 0.02), (tip[0] + 0.025, tip[1] + 0.025, tip[2] + 0.03), PR("flowers"), skip=())
    mg = I("mug", nocol=True)
    mx_, my_ = N0 + 0.20, NY1 - 0.24
    lathe(mg, mx_, my_, [(0.04, TOP), (0.042, TOP + 0.10)], PR("mug"), segs=8, cap=True)
    mg.box((mx_ + 0.04, my_ - 0.006, TOP + 0.025), (mx_ + 0.065, my_ + 0.006, TOP + 0.08), {k: PR("white") for k in ALL})
    cube(mg, (N0 + 0.12, NY0 + 0.06, TOP), (N0 + 0.17, NY0 + 0.24, TOP + 0.018), PR("black"))   # пульт

    # --- бра над входной дверью и выключатели ---
    sc = I("sconce", nocol=True)
    by, bz = (ENTRY[0] + ENTRY[1]) / 2, Z + 2.33
    sc.box((HX1 - 0.02, by - 0.045, bz - 0.06), (HX1, by + 0.045, bz + 0.06), {k: PR("brass") for k in ('-X', '+Y', '-Y', '+Z', '-Z')})
    cyl(sc, (HX1 - 0.02, by, bz), (HX1 - 0.13, by, bz + 0.05), 0.008, 0.008, PR("brass"), segs=4)
    gx = HX1 - 0.15
    cyl(sc, (gx, by, bz + 0.09), (gx, by, bz + 0.05), 0.012, 0.012, PR("brass"), segs=5)
    glow = (M["glow"], (0, 0, 1, 1))
    lathe(sc, gx, by, [(0.08, bz - 0.12), (0.075, bz - 0.06), (0.05, bz), (0.02, bz + 0.05)], glow, segs=8, inside=True)
    sw = I("switch_entry", nocol=True)
    sw.box((HX1 - 0.012, ENTRY[0] - 0.20, Z + 1.40), (HX1, ENTRY[0] - 0.12, Z + 1.48),
           {k: PR("switch") for k in ('-X', '+Y', '-Y', '+Z', '-Z')})
    sw2 = I("switch_corridor", nocol=True)
    sw2.box((HX0, -0.24, Z + 1.40), (HX0 + 0.012, -0.16, Z + 1.48),
            {k: PR("switch") for k in ('+X', '+Y', '-Y', '+Z', '-Z')})

    # --- крючки с зонтом и плетёной сумочкой (стена y = HY0, между дверями) ---
    hk = I("hooks_umbrella", nocol=True)
    hc = (DOUBLE_DOOR[1] + WC_DOOR[0]) / 2                                     # середина простенка
    hz = Z + 1.72
    hk.box((hc - 0.10, HY0, hz - 0.02), (hc + 0.10, HY0 + 0.018, hz + 0.02), {k: PR("pine") for k in ('+Y', '+X', '-X', '+Z', '-Z')})
    for hx_ in (hc - 0.07, hc, hc + 0.07):
        cyl(hk, (hx_, HY0 + 0.018, hz), (hx_, HY0 + 0.07, hz + 0.03), 0.006, 0.006, PR("metal"), segs=4, caps=True)
    ux, uy = hc, HY0 + 0.085
    cyl(hk, (ux, HY0 + 0.07, hz + 0.02), (ux, uy, hz - 0.06), 0.008, 0.008, PR("black"), segs=4)       # ручка-крюк
    lathe(hk, ux, uy, [(0.012, Z + 0.95), (0.04, Z + 1.25), (0.05, Z + 1.55), (0.02, hz - 0.06)], PR("umbrella"), segs=6)
    lathe(hk, hc - 0.07, HY0 + 0.07, [(0.06, Z + 1.38), (0.085, Z + 1.46), (0.08, Z + 1.58)], PR("wicker"), segs=6)
    cyl(hk, (hc - 0.12, HY0 + 0.07, Z + 1.58), (hc - 0.07, HY0 + 0.07, hz + 0.02), 0.005, 0.005, PR("wicker"), segs=3)
    cyl(hk, (hc - 0.02, HY0 + 0.07, Z + 1.58), (hc - 0.07, HY0 + 0.07, hz + 0.02), 0.005, 0.005, PR("wicker"), segs=3)

    # --- пылесос у двери в зал: корпус и шланг дугой ---
    vc = I("vacuum", nocol=True)
    vx0, vy0 = -5.00, 0.74
    lathe(vc, vx0, vy0, [(0.13, Z + 0.02), (0.17, Z + 0.07), (0.17, Z + 0.15), (0.12, Z + 0.22), (0.04, Z + 0.25)],
          PR("vac"), segs=8, cap=True)
    for (wx, wy) in ((vx0 - 0.11, vy0 - 0.11), (vx0 + 0.11, vy0 - 0.11), (vx0, vy0 + 0.14)):
        cyl(vc, (wx, wy - 0.012, Z + 0.03), (wx, wy + 0.012, Z + 0.03), 0.03, 0.03, PR("black"), segs=6)
    P = [Vector(q) for q in ((vx0 + 0.10, vy0 - 0.06, Z + 0.20), (vx0 + 0.30, vy0 - 0.16, Z + 1.45),
                             (vx0 - 0.30, vy0 - 0.10, Z + 1.30), (vx0 - 0.24, vy0 + 0.07, Z + 0.22))]
    pts = [(1 - t) ** 3 * P[0] + 3 * (1 - t) ** 2 * t * P[1] + 3 * (1 - t) * t * t * P[2] + t ** 3 * P[3]
           for t in [k / 14 for k in range(15)]]
    for p0, p1 in zip(pts, pts[1:]):
        cyl(vc, tuple(p0), tuple(p1), 0.017, 0.017, PR("hose"), segs=6)
    cyl(vc, tuple(pts[-1]), tuple(pts[-1] + Vector((-0.05, 0.03, -0.04))), 0.02, 0.02, PR("vac"), segs=6, caps=True)

    # --- плетёная корзина у выступа, в ней серая тряпка ---
    bk = I("basket", nocol=True)
    kx, ky = -5.72, 0.90
    n0 = len(bk.v)
    lathe(bk, kx, ky, [(0.22, Z), (0.27, Z + 0.05), (0.29, Z + 0.15), (0.30, Z + 0.18)], PR("wicker"), segs=10, inside=True)
    lathe(bk, kx, ky, [(0.30, Z + 0.18), (0.32, Z + 0.20), (0.30, Z + 0.215), (0.27, Z + 0.20)], PR("wicker"), segs=10)  # толстый край
    lathe(bk, kx, ky, [(0.22, Z + 0.001), (0.0, Z + 0.002)], PR("wicker"), segs=10)
    lathe(bk, kx, ky, [(0.27, Z + 0.08), (0.22, Z + 0.15), (0.12, Z + 0.17), (0.02, Z + 0.16)], PR("cloth"), segs=10)
    bk.v[n0:] = [(x_, ky + (y_ - ky) * 0.72, z_) for (x_, y_, z_) in bk.v[n0:]]                 # овальная

    for k in SHIFT_WEST:                                                       # удлинённая прихожая (EXT)
        for (b_, _) in I.items[k].values():
            b_.v[:] = [(x_ - EXT, y_, z_) for (x_, y_, z_) in b_.v]

    layout = export_items(I, coll)
    return {"items": len(layout), "layout": layout,
            "polys": {k: sum(len(b.f) for (b, _) in v.values()) for k, v in I.items.items()}}


M = {}


def main():
    sc = bpy.data.scenes.get("ApartmentProps") or bpy.data.scenes.new("ApartmentProps")
    bpy.context.window.scene = sc
    bpy.context.view_layer.update()
    for ob in list(sc.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for c in list(sc.collection.children):
        if c.name.startswith("ap_"):
            bpy.data.collections.remove(c)
    tex_door_white(); tex_door_glass(); tex_entry_in(); tex_wardrobe(); tex_glow(); tex_props()
    M.update({
        "trim": mat("ApTrim", "ap_trim", rough=0.7),
        "door_white": mat("ApDoorWhite", "ap_door_white", rough=0.6), "door_glass": mat("ApDoorGlass", "ap_door_glass", rough=0.4),
        "entry": mat("ApEntryIn", "ap_entry_in", rough=0.6), "wardrobe": mat("ApWardrobe", "ap_wardrobe", rough=0.5),
        "glow": mat("ApGlow", "ap_glow", "ap_glow"), "props": mat("ApProps", "ap_props", rough=0.8),
    })
    res = props()
    vl = sc.view_layers[0]
    for o in sc.objects:                                     # не оставлять выделение: другой экспорт его подхватит
        o.select_set(False, view_layer=vl)
    vl.objects.active = None
    print("BUILD_APARTMENT_PROPS " + json.dumps(res))
    return res


if __name__ == "__main__":
    RESULT = main()
