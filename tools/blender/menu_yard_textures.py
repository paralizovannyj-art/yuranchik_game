# Текстуры кадра главного меню (YUR-19): двор Юрчика зимой на закате, вид из его окна.
# Референсы — docs/references/main_menu/ (главный кадр image-20261127-134919.png и фото двора из окна).
# Новые здесь только те, которых нет в игре; деревья (eb_tree, eb_poplar), фасады (facade_*, eb_house),
# гофра (eb_corrugated) и снег (snow) берутся готовые.
#   menu_ground  — двор сверху: снег, протоптанные тропинки, колеи у парковки (план — в build_menu_yard.py, PLAN)
#   menu_garage  — бетонные блоки трансформаторной/гаражей в граффити, снизу грязный снег
#   menu_ac      — лицо наружного блока кондиционера: решётка вентилятора, белый пластик в потёках
#   menu_plaster — штукатурка под цвет (красится цветом материала): розовый домик, стены комнаты
# Запуск в открытом Blender (через Blender MCP):
#   MENU_ROOT = r"<папка проекта>"; exec(open(MENU_ROOT + r"\tools\blender\menu_yard_textures.py", encoding="utf-8").read())
# Рисует numpy, сохраняет tex_lib.save (с PS2-обработкой по таблице ps2_style.TEXTURES).
import math
import os
import sys
import importlib

ROOT = globals().get("MENU_ROOT") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HERE = os.path.join(ROOT, "tools", "blender")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import numpy as np
import bpy
import tex_lib
import ps2_style
importlib.reload(ps2_style)
importlib.reload(tex_lib)
tex_lib.TEX_DIR = os.path.join(ROOT, "assets", "textures")
from tex_lib import fbm, rgb, fill, save

# граффити и кривые — из текстур моста (сам скрипт там ничего не пересобирает: EB_ONLY = ["-"])
_eb = {"EB_ROOT": ROOT, "EB_ONLY": ["-"], "__name__": "menu_eb"}
exec(open(os.path.join(HERE, "east_bridge_textures.py"), encoding="utf-8").read(), _eb)
spray_tag, disc_stroke, catmull = _eb["spray_tag"], _eb["disc_stroke"], _eb["catmull"]

SNOW = rgb((0.86, 0.87, 0.92))


def rng_for(name):
    return np.random.default_rng(sum(map(ord, name)) * 7919 + 23)


# ------------------------------------------------------------------ двор сверху
# Карта двора по плану menu_yard_plan.py (спутник + видео из окна): снег, асфальт проезда, парковок,
# площадки и проспекта (почищен — серая каша), пустырь за забором с сухим бурьяном, тропинки, колеи.
# Пиксель (px, py) ↔ x = GX0 + px·GM, z = GZ0 + py·GM.
PLAN = {"__name__": "menu_plan"}
exec(open(os.path.join(HERE, "menu_yard_plan.py"), encoding="utf-8").read(), PLAN)


def ground():
    P = PLAN
    rng = rng_for("menu_ground")
    w, h = P["GPX"], P["GPZ"]
    m = P["GM"]
    arr = SNOW * (0.92 + fbm(w, h, 36, 54, rng, oct=3)[..., None] * 0.08)
    # заструги и сугробы — крупные мягкие пятна светлее/темнее
    arr *= (0.96 + fbm(w, h, 8, 12, rng, oct=2)[..., None] * 0.06)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    X = P["GX0"] + (xx + 0.5) * m
    Z = P["GZ0"] + (yy + 0.5) * m

    def to_px(p):
        return ((p[0] - P["GX0"]) / m, (p[1] - P["GZ0"]) / m)

    def rect(x0, x1, z0, z1, soft=0.4):
        """Маска прямоугольника (Godot x, z) с мягким краем, м."""
        za, zb = min(z0, z1), max(z0, z1)
        k = np.clip(np.minimum.reduce([X - x0, x1 - X, Z - za, zb - Z]) / soft + 0.5, 0, 1)
        return k

    # пустырь за забором (до полосы складов): из-под снега торчит сухой бурьян, кучи мусора
    lot = rect(-70, 205, P["FIELD_FENCE"][0][1] - 2, P["STRIP"][3], soft=3.0) * np.clip((X - 0) / 8 + 1, 0, 1)
    weeds = np.clip((fbm(w, h, 120, 180, rng, oct=3) - 0.55) * 4.0, 0, 1) * lot
    arr = arr * (1 - weeds[..., None] * 0.55) + rgb((0.36, 0.30, 0.27)) * weeds[..., None] * 0.55
    # поле во дворе: редкие кочки и прошлогодняя трава у тропинок
    tufts = np.clip((fbm(w, h, 160, 240, rng, oct=2) - 0.68) * 5.0, 0, 1) * rect(16, 95, -85, 55, soft=4)
    arr = arr * (1 - tufts[..., None] * 0.35) + rgb((0.42, 0.38, 0.33)) * tufts[..., None] * 0.35

    # асфальт: проезд вдоль дома, карманы парковки, площадка, проезд у дома с красными шапками, стоянка рынка,
    # проспект с тротуарами
    asph = np.zeros((h, w), np.float32)
    for (x0, x1, z0, z1) in [
            (P["WALK_X"][0], P["DRIVE_X"][1], P["DRIVE_Z"][0], P["DRIVE_Z"][1]),
            P["PARKING"], P["PLAYGROUND"],
            (68.0, 76.0, -55.0, 59.0), (P["DRIVE_X"][1], 70.0, -55.0, -49.0),
            P["MARKET_PARKING"], (76.0, 110.0, -49.0, -41.0),
            (-80.0, 240.0, P["AVENUE_Z"][0] - 5.0, P["AVENUE_Z"][1] + 4.0),
            (-80.0, 240.0, -180.0, -176.0)]:
        asph = np.maximum(asph, rect(x0, x1, z0, z1))
    # заворот проезда за торец дома
    turn = catmull([to_px(p) for p in P["DRIVE_TURN"]], 40)
    tmask = np.zeros((h, w), np.float32)
    disc_stroke(tmask, turn, P["DRIVE_W"] / 2 / m, soft=0.4 / m)
    asph = np.maximum(asph, tmask)
    slush = rgb((0.50, 0.50, 0.55)) * (0.78 + fbm(w, h, 90, 135, rng, oct=3)[..., None] * 0.32)
    # снег по краям асфальта (отвалы) и белые пятна поверх каши
    patches = np.clip((fbm(w, h, 60, 90, rng, oct=3) - 0.5) * 3.0, 0, 1)
    k = asph * (1 - patches * 0.5)
    arr = arr * (1 - k[..., None] * 0.75) + slush * k[..., None] * 0.75

    # клумбы на площадке: земля с листвой под снегом в бортиках
    for (cx, cz) in P["PLANTERS"]:
        bed = rect(cx - 1.2, cx + 1.2, cz - 1.2, cz + 1.2, soft=0.15)
        arr = arr * (1 - bed[..., None] * 0.45) + rgb((0.35, 0.28, 0.24)) * bed[..., None] * 0.45
    # разметка карманов парковки — чуть видна сквозь кашу
    x0, x1, z0, z1 = P["PARKING"]
    lines = rect(x0 + 0.3, x1, z0, z1) * (np.abs(((Z - z1) % 2.6) - 1.3) > 1.2)
    arr = arr * (1 - lines[..., None] * 0.25) + SNOW * lines[..., None] * 0.25
    # разделительная проспекта и разметка
    zc = sum(P["AVENUE_Z"]) / 2
    med = rect(-80, 240, zc - 1.0, zc + 1.0, soft=0.3)
    arr = arr * (1 - med[..., None] * 0.8) + SNOW * med[..., None] * 0.8

    # тропинки
    trodden = np.zeros((h, w), np.float32)
    for path in P["PATHS"]:
        pts = catmull([to_px(p) for p in path], 30)
        pts = pts + rng.normal(0, 0.3, pts.shape)
        disc_stroke(trodden, pts, (1.1 + rng.uniform(-0.1, 0.3)) / m * 0.5 + 1.2, soft=1.6)
    trodden = ps2_style.blur(trodden[..., None], 0.8)[..., 0]
    mud = rgb((0.52, 0.50, 0.53)) * (0.8 + fbm(w, h, 120, 180, rng, oct=2)[..., None] * 0.3)
    arr = arr * (1 - trodden[..., None] * 0.6) + mud * trodden[..., None] * 0.6
    # колеи: проезд вдоль дома и у дома напротив
    ruts = np.zeros((h, w), np.float32)
    for xr in (6.4, 8.4, 71.0, 73.0):
        r = [(xr, P["DRIVE_Z"][0]), (xr, P["DRIVE_Z"][1])]
        pts = catmull([to_px(p) for p in r], 600)
        disc_stroke(ruts, pts + rng.normal(0, 0.2, pts.shape), 1.3, soft=1.0)
    # колеи на завороте: осевая ± 1 м по нормали
    d = np.gradient(turn, axis=0)
    nrm = np.stack([-d[:, 1], d[:, 0]], 1) / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-6)
    for off in (-1.0, 1.0):
        pts = turn + nrm * (off / m)
        disc_stroke(ruts, pts + rng.normal(0, 0.2, pts.shape), 1.3, soft=1.0)
    arr = arr * (1 - ruts[..., None] * 0.45) + rgb((0.36, 0.36, 0.40)) * ruts[..., None] * 0.45
    save("menu_ground", arr)


# ------------------------------------------------------------------ трансформаторная / гаражи в граффити
def garage():
    rng = rng_for("menu_garage")
    w, h = 256, 128
    base = rgb((0.50, 0.50, 0.49)) * (0.82 + fbm(w, h, 10, 5, rng, oct=4)[..., None] * 0.3)
    # бетонные блоки 2 × 0.6 м: стена 8 м шириной на 4 м высотой → блок 64 × 19 px
    yy, xx = np.mgrid[0:h, 0:w]
    row = yy // 19
    seam = ((yy % 19) < 1) | (((xx + (row % 2) * 32) % 64) < 1)
    base[seam] *= 0.62
    arr = base.copy()
    # граффити: плотно внизу, крупные цветные куски (как на фото) и чёрные теги поверх
    cols = [(0.20, 0.35, 0.75), (0.78, 0.20, 0.25), (0.15, 0.55, 0.45), (0.85, 0.78, 0.75), (0.55, 0.25, 0.65)]
    for i in range(7):
        c = cols[i % len(cols)]
        x = rng.uniform(-10, w - 60)
        y = rng.uniform(h * 0.35, h * 0.72)
        spray_tag(arr, rng, x, y, rng.uniform(50, 90), rng.uniform(22, 34), c, outline=(0.06, 0.06, 0.08),
                  width=rng.uniform(2.6, 3.6), letters=int(rng.integers(3, 5)), alpha=0.85)
    for i in range(6):
        spray_tag(arr, rng, rng.uniform(0, w - 40), rng.uniform(h * 0.45, h * 0.85), rng.uniform(25, 45), 12,
                  (0.06, 0.06, 0.07), width=1.3, letters=3, alpha=0.8)
    arr *= 1 - ps2_style.drips(h, w, rng, 0.8, 0.5)[..., None] * 0.25
    # снизу налип снег, сверху — тёмная полоса от карниза
    k = np.clip((yy - (h - 9)) / 6.0, 0, 1)[..., None]
    arr = arr * (1 - k) + SNOW * 0.9 * k
    arr[:5] *= 0.6
    save("menu_garage", arr)


# ------------------------------------------------------------------ кондиционер
def ac():
    rng = rng_for("menu_ac")
    n = 128
    arr = rgb((0.86, 0.86, 0.84)) * (0.9 + fbm(n, n, 6, 6, rng, oct=3)[..., None] * 0.12)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    cx, cy, r = n * 0.58, n * 0.52, n * 0.34
    d = np.hypot(xx - cx, yy - cy)
    inside = d < r
    rings = (np.sin(d * 1.4) > 0.2) & inside
    arr[inside] *= 0.45
    arr[rings] = rgb((0.74, 0.74, 0.72))
    hub = d < r * 0.18
    arr[hub] = rgb((0.6, 0.6, 0.58))
    edge = (d > r - 2.0) & (d < r + 1.5)
    arr[edge] *= 0.55
    # левая часть — решётка жалюзи
    slats = (xx < n * 0.2) & ((yy.astype(int) % 6) < 2) & (yy > 12) & (yy < n - 12)
    arr[slats] *= 0.6
    # потёки ржавчины и грязи
    arr *= 1 - ps2_style.drips(n, n, rng, 1.2, 0.7)[..., None] * 0.3
    arr[:4] *= 0.8
    arr[-4:] *= 0.7
    save("menu_ac", arr)


# ------------------------------------------------------------------ штукатурка (под цвет)
def plaster():
    rng = rng_for("menu_plaster")
    n = 128
    arr = rgb((0.82, 0.82, 0.82)) * (0.84 + fbm(n, n, 8, 8, rng, oct=4)[..., None] * 0.24)
    inside, ring = ps2_style.water_stains(n, n, rng, 3, 0.3)
    arr *= 1 - (inside + ring)[..., None] * 0.3
    arr *= 1 - ps2_style.drips(n, n, rng, 0.6, 0.5)[..., None] * 0.2
    save("menu_plaster", arr)


# ------------------------------------------------------------------ окна панелек (атлас)
# 4 окна по 64 × 64 в ряд (u = 0, 0.25, 0.5, 0.75): тёмное стекло с небом, шторы в темноте,
# горит тёплая лампа, горит за оранжевой шторой. Белая ПВХ-рама с импостом, у старых — деревянная.
# menu_windows_emission — свечение тех же окон (чёрное, где не горит).
WIN_KINDS = ["dark", "curtain", "lit", "lit_curtain"]


def windows():
    rng = rng_for("menu_windows")
    n = 64
    alb = np.zeros((n, n * 4, 3), np.float32)
    emi = np.zeros((n, n * 4, 3), np.float32)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    for i, kind in enumerate(WIN_KINDS):
        a = np.zeros((n, n, 3), np.float32)
        e = np.zeros((n, n, 3), np.float32)
        # стекло: тёмное, сверху ловит розовое небо
        sky = rgb((0.30, 0.22, 0.30)) * (1 - yy[..., None] / n) + rgb((0.06, 0.06, 0.08)) * (yy[..., None] / n)
        a[:] = sky * (0.8 + fbm(n, n, 4, 4, rng, oct=2)[..., None] * 0.3)
        if kind == "curtain":
            folds = 0.75 + 0.25 * np.sin(xx * 0.9 + rng.uniform(0, 6))
            a[:] = rgb((0.20, 0.17, 0.16)) * folds[..., None]
        if kind == "lit":
            lamp = rgb((1.0, 0.72, 0.42)) * (0.75 + 0.25 * np.exp(-((xx - 40) ** 2 + (yy - 14) ** 2) / 300))[..., None]
            a[:] = lamp * 0.8
            e[:] = lamp
            # тюль и силуэт шкафа
            e[:, :10] *= 0.5
            e *= (0.85 + 0.15 * np.sin(xx * 1.7))[..., None]
        if kind == "lit_curtain":
            folds = 0.7 + 0.3 * np.sin(xx * 0.8 + 1.3)
            c = rgb((1.0, 0.48, 0.2)) * folds[..., None]
            a[:] = c * 0.7
            e[:] = c * 0.85
        # рама: по краю 5 px, импост посередине, у половины — форточка
        frame = (xx < 5) | (xx >= n - 5) | (yy < 5) | (yy >= n - 6) | ((xx >= 30) & (xx < 34))
        if i % 2 == 0:
            frame |= (yy >= 20) & (yy < 23) & (xx < 32)
        fc = rgb((0.82, 0.81, 0.78)) if i != 1 else rgb((0.46, 0.38, 0.30))
        a[frame] = fc
        e[frame] = 0
        # отлив снизу в снегу
        a[n - 3:] = rgb((0.88, 0.88, 0.92))
        e[n - 3:] = 0
        alb[:, i * n:(i + 1) * n] = a
        emi[:, i * n:(i + 1) * n] = e
    save("menu_windows", alb)
    save("menu_windows_emission", emi)


# ------------------------------------------------------------------ фасады домов вокруг двора (по видео из окна)
# Плитка — 4 клетки по 3 м × 4 этажа по 2.8 м (12 × 11.2 м), 16 px/м → 192 × 180. Клетка: окно или застеклённая
# лоджия, у части окон — наружный блок кондиционера. *_emission — горящие окна (ночь в меню).
#   menu_fac_cream — дом с красными шапками: кремовые стены, жёлтые вертикальные полосы, белые лоджии, кондиционеры
#   menu_fac_ochre — ряд за проспектом: охра/персик, лоджии полосами
#   menu_fac_brick — 16-этажки справа: кирпично-красные простенки и белые стопки лоджий
FAC_BAY, FAC_FL, FAC_PX = 48, 45, 16


def facade_kit(name, wall, rng, layout, accent=None, loggia_c=(0.92, 0.92, 0.9), ac_p=0.35, lit_p=0.22):
    """layout[bay] — 'win' | 'loggia' | 'win_accent' (клетка в цвете accent) | 'brick' (узкое окно в кирпиче)."""
    w, h = FAC_BAY * 4, FAC_FL * 4
    alb = fill(h, w, wall) * (0.9 + fbm(w, h, 12, 12, rng, oct=4)[..., None] * 0.16)
    emi = np.zeros((h, w, 3), np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    glass = rgb((0.16, 0.18, 0.22))
    frame = rgb((0.9, 0.9, 0.88))
    warm = [rgb((1.0, 0.72, 0.42)), rgb((1.0, 0.55, 0.25)), rgb((0.9, 0.85, 0.7))]
    for f in range(4):
        y0 = h - (f + 1) * FAC_FL                       # верх этажа (строка 0 — верх картинки)
        for bi, kind in enumerate(layout):
            x0 = bi * FAC_BAY
            cell = (slice(y0, y0 + FAC_FL), slice(x0, x0 + FAC_BAY))
            if kind in ("win_accent", "brick") and accent is not None:
                alb[cell] = rgb(accent) * (0.9 + fbm(FAC_BAY, FAC_FL, 3, 3, rng, oct=3)[..., None] * 0.16)
            lit = rng.random() < lit_p
            lc = warm[int(rng.integers(0, 3))]
            if kind == "loggia":
                # парапет внизу, остекление в белых рамах на всю клетку
                gx0, gx1, gy0, gy1 = x0 + 3, x0 + FAC_BAY - 3, y0 + 4, y0 + FAC_FL - 17
                alb[y0 + FAC_FL - 17:y0 + FAC_FL - 2, x0 + 2:x0 + FAC_BAY - 2] = rgb(loggia_c) * 0.95
                alb[gy0:gy1, gx0:gx1] = glass
                if lit:
                    emi[gy0:gy1, gx0:gx1] = lc * 0.8
                    alb[gy0:gy1, gx0:gx1] = lc * 0.6
                for k in range(5):
                    xk = gx0 + k * (gx1 - gx0) // 4
                    alb[gy0:gy1, max(gx0, xk - 1):xk + 1] = frame
                    emi[gy0:gy1, max(gx0, xk - 1):xk + 1] = 0
                alb[gy0:gy0 + 2, gx0:gx1] = frame
                alb[gy1 - 2:gy1, gx0:gx1] = frame
                alb[y0 + FAC_FL - 2:y0 + FAC_FL, x0:x0 + FAC_BAY] *= 0.7    # плита перекрытия
            else:
                ww = 16 if kind == "brick" else 24
                wx0 = x0 + (FAC_BAY - ww) // 2
                wy0, wy1 = y0 + 8, y0 + 8 + 24
                alb[wy0:wy1, wx0:wx0 + ww] = glass
                if lit:
                    emi[wy0:wy1, wx0:wx0 + ww] = lc
                    alb[wy0:wy1, wx0:wx0 + ww] = lc * 0.7
                fr = (np.abs(xx[wy0:wy1, wx0:wx0 + ww] - (wx0 + ww // 2)) < 1) | (yy[wy0:wy1, wx0:wx0 + ww] < wy0 + 2) | \
                     (yy[wy0:wy1, wx0:wx0 + ww] >= wy1 - 2) | (xx[wy0:wy1, wx0:wx0 + ww] < wx0 + 2) | \
                     (xx[wy0:wy1, wx0:wx0 + ww] >= wx0 + ww - 2)
                sub_a, sub_e = alb[wy0:wy1, wx0:wx0 + ww], emi[wy0:wy1, wx0:wx0 + ww]
                sub_a[fr] = frame
                sub_e[fr] = 0
                alb[wy1:wy1 + 2, wx0 - 1:wx0 + ww + 1] = rgb((0.85, 0.85, 0.88))       # отлив в снегу
            if rng.random() < ac_p:
                ax = x0 + (2 if rng.random() < 0.5 else FAC_BAY - 15)
                ay = y0 + int(rng.integers(6, 22))
                alb[ay:ay + 9, ax:ax + 13] = rgb((0.93, 0.93, 0.9))
                alb[ay + 2:ay + 7, ax + 6:ax + 11] = rgb((0.55, 0.55, 0.55))
                alb[ay + 9:ay + 10, ax:ax + 13] = rgb((0.4, 0.38, 0.36))
    # межэтажные швы и потёки
    for f in range(4):
        alb[h - f * FAC_FL - 1, :] *= 0.8
    alb *= 1 - ps2_style.drips(h, w, rng, 0.5, 0.5)[..., None] * 0.15
    save(name, alb)
    save(name + "_emission", emi)


def facades():
    facade_kit("menu_fac_cream", (0.93, 0.88, 0.80), rng_for("menu_fac_cream"),
               ["win", "loggia", "win_accent", "loggia"], accent=(0.96, 0.82, 0.55), ac_p=0.45)
    facade_kit("menu_fac_ochre", (0.92, 0.70, 0.50), rng_for("menu_fac_ochre"),
               ["loggia", "win", "loggia", "win"], loggia_c=(0.88, 0.64, 0.48), ac_p=0.25)
    facade_kit("menu_fac_brick", (0.9, 0.88, 0.84), rng_for("menu_fac_brick"),
               ["brick", "loggia", "loggia", "brick"], accent=(0.66, 0.36, 0.28), ac_p=0.3)


# ------------------------------------------------------------------ деревья: кора и снежные веточки
def bark():
    """Кора голых деревьев двора (тянется вдоль ствола и веток): тёмная, с продольными трещинами и пятнами
    лишайника. 64 × 256, тайл 0.6 × 2.4 м."""
    rng = rng_for("menu_bark")
    w, h = 64, 256
    arr = rgb((0.33, 0.3, 0.28)) * (0.75 + fbm(w, h, 4, 16, rng, oct=4)[..., None] * 0.4)
    fis = np.clip((0.42 - fbm(w, h, 14, 3, rng, oct=3)) * 6.0, 0, 1)                 # трещины вдоль
    arr *= 1 - fis[..., None] * 0.6
    li = np.clip((fbm(w, h, 6, 12, rng, oct=3) - 0.62) * 4.0, 0, 1)                 # серый лишайник
    arr = arr * (1 - li[..., None] * 0.4) + rgb((0.45, 0.45, 0.41)) * li[..., None] * 0.4
    save("menu_bark", arr)


def twigs():
    """Пучок тонких веточек на концах веток (карточки с альфой): голые прутья, на каждом сверху налип снег
    после метели. Рендер настоящих веточек в студии, 256 × 256 на 4 × 4 м, низ середины — точка крепления."""
    T, tm = _eb["T"], _eb["_tree_mesh"]
    rng = rng_for("menu_twigs")
    bark_m = T.material("menu_t_twig", (0.15, 0.13, 0.12), rough=0.95, noise=0.2, noise_scale=8,
                        snow_top=0.95, snow_axis="Y")
    sc = T.studio(4.0, 4.0, 256, 256, samples=24, sun_elev=60, transparent=True)
    parts = []
    for i in range(5):
        a = (i - 2) * 0.32 + rng.normal(0, 0.1)
        parts.append(tm(rng, 2.0 + rng.normal(0, 0.08), 0.0, a, rng.uniform(1.9, 2.8), 0.06, 3,
                        (0.3, 0.75), (0.5, 0.7), 2, up_bias=0.15))
    v, f = T.merge(parts)
    T.mesh_object(sc, "twigs", v, f, bark_m)
    arr = T.render(sc, "menu_twigs")
    # метель: снег налип на верхнюю сторону каждого прутика — белая кромка 2 px там, где над веткой пусто,
    # и местами комья побольше
    al = arr[..., 3] > 0.5
    above = np.zeros_like(al)
    above[1:] = al[:-1]
    edge = al & ~above
    edge2 = edge.copy()
    edge2[1:] |= edge[:-1]
    clump = np.clip((fbm(256, 256, 24, 24, rng, oct=2) - 0.5) * 6.0, 0, 1) > 0.5
    edge3 = edge2.copy()
    edge3[2:] |= edge2[:-2] & clump[2:]
    snow = rgb((0.88, 0.9, 0.96)) * (0.92 + fbm(256, 256, 30, 30, rng, oct=2)[..., None] * 0.1)
    arr[..., :3] = np.where(edge3[..., None] & al[..., None], snow, arr[..., :3])
    _eb["save_rgba"]("menu_twigs", arr)


ALL = (ground, garage, ac, plaster, windows, facades, bark, twigs)
MAKES = {"windows": ["menu_windows", "menu_windows_emission"],
         "facades": ["menu_fac_cream", "menu_fac_ochre", "menu_fac_brick"]}


def main():
    only = globals().get("MENU_ONLY")
    done = []
    for fn in ALL:
        names = MAKES.get(fn.__name__, ["menu_" + fn.__name__])
        if only and not set(names) & set(only):
            continue
        fn()
        done += names
    return {"made": done}


result = main()
print(result)
