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
# Карта двора: квадрат GROUND_SIZE × GROUND_SIZE м, левый-верхний угол — GROUND_ORIGIN (Godot x, z).
# Пиксель (px, py) ↔ x = X0 + px·m, z = Z0 + py·m. Должно совпадать с build_menu_yard.py.
GROUND_ORIGIN = (0.0, -150.0)
GROUND_SIZE = 160.0
GROUND_PX = 512

# тропинки и колеи (Godot x, z, м) — по фото из окна: от подъезда через двор к трансформаторной,
# дуга к дальнему краю, вдоль гаражей; колеи — вдоль дома (проезд и парковка)
PATHS = [
    [(9, 8), (14, -4), (22, -16), (28, -30), (34, -46), (44, -62), (60, -78)],
    [(22, -16), (36, -14), (52, -18), (70, -26), (92, -30)],
    [(28, -30), (18, -42), (12, -60), (14, -84), (20, -110)],
    [(34, -46), (52, -44), (66, -52), (82, -66), (100, -76)],
    [(9, -20), (10, -40), (9, -70), (8, -100), (10, -140)],
    [(60, -78), (70, -100), (74, -124), (78, -148)],
]
RUTS = [[(4.6, 14), (4.6, -140)], [(6.2, 14), (6.2, -140)]]


def ground():
    rng = rng_for("menu_ground")
    n = GROUND_PX
    m = GROUND_SIZE / n
    arr = SNOW * (0.92 + fbm(n, n, 24, 24, rng, oct=3)[..., None] * 0.08)
    # заструги и сугробы — крупные мягкие пятна светлее/темнее
    arr *= (0.96 + fbm(n, n, 6, 6, rng, oct=2)[..., None] * 0.06)
    trodden = np.zeros((n, n), np.float32)

    def to_px(p):
        return ((p[0] - GROUND_ORIGIN[0]) / m, (p[1] - GROUND_ORIGIN[1]) / m)

    for path in PATHS:
        pts = catmull([to_px(p) for p in path], 24)
        pts = pts + rng.normal(0, 0.35, pts.shape)
        disc_stroke(trodden, pts, 3.4 + rng.uniform(-0.4, 0.8), soft=2.0)
    ruts = np.zeros((n, n), np.float32)
    for r in RUTS:
        pts = catmull([to_px(p) for p in r] * 1, 200)
        disc_stroke(ruts, pts + rng.normal(0, 0.25, pts.shape), 1.6, soft=1.2)
    trodden = ps2_style.blur(trodden[..., None], 0.8)[..., 0]
    slush = rgb((0.55, 0.56, 0.62)) * (0.8 + fbm(n, n, 40, 40, rng, oct=2)[..., None] * 0.3)
    arr = arr * (1 - trodden[..., None] * 0.55) + slush * trodden[..., None] * 0.55
    arr = arr * (1 - ruts[..., None] * 0.5) + rgb((0.42, 0.42, 0.47)) * ruts[..., None] * 0.5
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


ALL = (ground, garage, ac, plaster, windows)
MAKES = {"windows": ["menu_windows", "menu_windows_emission"]}


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
