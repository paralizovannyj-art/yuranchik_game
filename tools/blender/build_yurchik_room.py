# -*- coding: utf-8 -*-
# Комната Юрчика в квартире 47 (задача YUR-17) — по фотографиям настоящей комнаты.
#
# Что в комнате (как на фото):
#   * окно в белой пластиковой раме, под ним батарея, на подоконнике цветок в оранжевом горшке и бутылка воды;
#   * слева от окна — комод под белой скатертью: спатифиллум, икона в рамке, коробки, книги;
#   * справа от окна — кресло, заваленное одеждой;
#   * вдоль длинной стены — разложенный диван с подлокотниками и цветастым пледом (розы, медальон, «леопардовая» кайма);
#     стена над диваном — бежевые фактурные панели с рядом дырок от дюбелей;
#   * в углу у двери — чёрный компьютерный стол; зелёно-чёрное игровое кресло — отдельная модель (build_gaming_chair.py);
#   * компьютер образца 2010–2011: квадратный LCD-монитор 19" (5:4), чёрный корпус с DVD-приводом стоит НА столе,
#     колонки 2.0, клавиатура, мышь. Никакого маленького RGB-компа под столом;
#   * белая стена с дверью: над столом надписи красным маркером (как на фото — текст в списке WRITING),
#     выключатель на 1.5 м у проёма, розетка под ним;
#     на столе миска с ложкой, на системнике красная мягкая игрушка;
#   * стена напротив дивана — у двери коллаж из страниц манги, на левую половину стены (страницы свои, процедурные);
#     люстра с тремя плафонами, светлый ламинат.
#
# Запуск (Blender 5.2, из корня проекта; надписи рисуются шрифтами Windows Segoe Print и Ink Free):
#   blender -b --factory-startup --python tools/blender/build_yurchik_room.py
# или через Blender MCP: exec(open(r"<путь>/tools/blender/build_yurchik_room.py", encoding="utf-8").read(), {"__file__": <путь>, "__name__": "__main__"})
# Результат: assets/textures/yr_*.png (yr_writing.png — с прозрачностью) и комната по предметам —
# assets/models/yurchik_room/<предмет>.gltf: каждый предмет (стены, диван, плед, кресло, комод, стол, монитор,
# системник, колонки, люстра, батарея, мелочь на комоде и подоконнике…) — отдельная модель с точкой опоры
# у основания по центру (у люстры — сверху). Позиции предметов — assets/models/yurchik_room/layout.json (в координатах
# Godot); в stairwell.tscn они стоят дочерними узлами YurchikRoom. В Blender каждый предмет — своя коллекция yr_<имя>.
#
# Координаты — те же, что у подъезда (build_mvp_assets.py): комната на 4-м этаже, x −10.5…−6.32, y 0.95…3.9,
# пол на z = 8.4.
# Объекты внутри файла предмета (см. Items): <Предмет> — жёсткое (Godot делает коллизию по сетке),
# <Предмет>_nocol — мелочь без коллизии, <Предмет>Soft_nocol — мягкое с гладким затенением,
# <Предмет>Col-colonly — невидимые ящики-коллизии мягкого. Особые имена, которые ищет игра (stairwell.gd):
# PCScreen_nocol — экран монитора (игра его «включает»), LightSwitchKey_nocol — клавиша выключателя,
# Chandelier_nocol — люстра (плафоны гаснут и загораются). EastWriting_nocol — прозрачная наклейка с надписями.
# Мягкие формы — soft() (скруглённый ящик с буграми) и drape() (ткань, наброшенная на прямоугольник, со свесами).
import bpy, os, sys, math, json
import numpy as np
from mathutils import Vector, Euler, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from tex_lib import save
import ps2_hero
from ps2_hero import C, finish, plaster, peeled, scribble
from ps2_style import noise, smoothstep, blur, floor_grime, mottle

_ns = {"NO_MAIN": True}
exec(compile(open(os.path.join(HERE, "build_yard.py"), encoding="utf-8").read(), "build_yard.py", "exec"), _ns)
B, mat = _ns["B"], _ns["mat"]
OUT = os.path.join(ROOT, "assets", "models")
R = np.random.default_rng(1717)

# --- размеры комнаты (как в build_mvp_assets.stairwell) ---
X0, X1, XF = -10.5, -6.32, -6.2        # западная стена (окно), восточная стена (дверь), край пола под проёмом
Y0, Y1 = 0.95, 3.9                     # южная стена (манга) — в ~1.3 м от дивана, как на фото; северная (диван, панели)
Z, H = 8.4, 2.7                       # потолок 2.7 м, как в панельке на фото
ZT = Z + H
DOOR_Y0, DOOR_Y1, DOOR_H = 1.05, 1.9, 2.05


# =====================================================================================
#  Текстуры
# =====================================================================================
# Раскладка панелей на северной стене (по фото): одна текстура на всю стену X0..X1 x пол..потолок.
# Вертикальные стыки — от угла у двери через каждые 1.13 м (первый — ровно над левым краем стола), слева остаётся
# узкая подрезанная панель. Горизонтальные — на 1.76 м от пола (над монитором ~0.55 м) и ниже ровно на высоту
# верхней панели (от 1.76 до потолка), так что средний ряд такой же высоты, как верхний. Все стыки — сквозные и ровные.
PANEL_SEAMS_X = (X1 - 1.13, X1 - 2.26, X1 - 3.39)
PANEL_SEAMS_Z = (1.76 - (H - 1.76), 1.76)
# Дырки от дюбелей — только над столом (по фото, x — мировой, z — от пола): неровные ряды, остальная стена чистая
PANEL_HOLES = ((-7.22, 1.94), (-6.96, 1.95), (-6.60, 1.70), (-6.63, 1.55), (-7.08, 1.41), (-6.96, 1.41),
               (-6.85, 1.42), (-6.71, 1.42), (-6.53, 1.43), (-6.38, 1.44), (-7.20, 1.28))


def tex_panels():
    """Бежевые фактурные панели над диваном (как на фото): светлый «венецианский» узор — дуги и завитки шпателя
    чуть темнее фона, мелкий рельеф. Текстура на всю стену: стыки и дырки стоят точно по PANEL_SEAMS_* / PANEL_HOLES."""
    WL = X1 - X0
    w, h = 1024, 664                                                               # ~245 px на метр по обеим осям
    PR = np.random.default_rng(301)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = noise(w, h, 12, 8, PR, oct=3) * 60
    arcs = np.zeros((h, w), np.float32)
    for _ in range(36):                                                            # дуги-мазки вокруг случайных центров
        cx, cy, rad = PR.uniform(0, w), PR.uniform(0, h), PR.uniform(40, 140)
        rr = np.hypot(xx - cx, yy - cy) + warp
        ring = np.exp(-((np.sin(rr / rad * 6.0)) ** 2) / 0.03) * np.exp(-(rr / (rad * 1.6)) ** 2)
        arcs = np.maximum(arcs, ring)
    n2 = noise(w, h, 96, 62, PR, oct=3)
    hgt = n2 * 0.5 + arcs * 0.5
    sh = 1 + ((hgt - np.roll(hgt, 1, 1)) + (hgt - np.roll(hgt, 1, 0))) * 1.2       # рельеф, свет сверху-слева
    arr = np.ones((h, w, 3), np.float32) * C(0.80, 0.74, 0.58)
    arr = arr * (1 - arcs[..., None] * 0.08) + arcs[..., None] * C(0.58, 0.50, 0.34) * 0.08
    arr *= sh[..., None]
    arr *= mottle(h, w, PR, 4, 0.08)[..., None]
    px = lambda x: int(round((x - X0) / WL * w))
    py = lambda z: int(round((1 - z / H) * h))
    for x in PANEL_SEAMS_X:                                                        # стыки панелей: тёмная щель + светлая кромка
        k = px(x)
        arr[:, k - 1:k + 1] *= 0.64; arr[:, k + 1:k + 2] *= 1.06
    for z in PANEL_SEAMS_Z:
        k = py(z)
        arr[k - 1:k + 1] *= 0.62; arr[k + 1:k + 2] *= 1.08
    for (x, z) in PANEL_HOLES:                                                     # дырки: чёрный квадратик со сколом краски
        cx, cy = px(x), py(z)
        s = int(PR.integers(5, 8))
        arr[cy - s // 2 - 1:cy + s // 2 + 2, cx - s // 2 - 1:cx + s // 2 + 2] *= 1.08
        arr[cy - s // 2:cy + s // 2 + 1, cx - s // 2:cx + s // 2 + 1] = C(0.10, 0.08, 0.06)
        arr[cy + s // 2 + 1:cy + s // 2 + 3, cx - s // 2:cx + s // 2 + 1] *= 0.82
    save("yr_panels", finish(arr, 1.15, crisp=0.3))


def tex_west():
    """Стена с окном (как на фото): светлая кремовая побелка; там, где содрали обои, — пятна белой шпаклёвки
    с жёлтой каймой и клочки старых обоев с мелким «червячковым» узором."""
    w = h = 512
    WR_ = np.random.default_rng(302)
    arr = plaster(WR_, w, h, (0.85, 0.80, 0.67), streak=0.06, stains=0.08, crack=0.06)
    patch = smoothstep(0.52, 0.58, noise(w, h, 6, 6, WR_, oct=4))
    rim = np.clip(patch - np.roll(patch, (3, 3), (0, 1)), 0, 1)
    white = C(0.89, 0.87, 0.80) * (0.95 + 0.08 * noise(w, h, 30, 30, WR_))[..., None]
    arr = arr * (1 - patch[..., None]) + white * patch[..., None]
    arr *= (1 - rim * 0.12)[..., None]
    paper = smoothstep(0.62, 0.66, noise(w, h, 5, 5, WR_, oct=3)) * (1 - patch)        # клочки обоев
    worm = np.abs(noise(w, h, 90, 90, WR_, oct=2) - 0.5) < 0.035
    pap = C(0.86, 0.82, 0.69) * np.where(worm, 1.08, 0.93)[..., None]
    arr = arr * (1 - paper[..., None]) + pap * paper[..., None]
    arr *= (1 - smoothstep(0.7, 0.9, noise(w, h, 4, 4, WR_, oct=3)) * 0.12)[..., None]   # лёгкая желтизна
    save("yr_west", finish(arr, 1.15, crisp=0.3))


RM = np.random.default_rng(2015)             # свой генератор для манги и надписей — остальные текстуры не «плывут»


def manga_page(pw, ph, rng):
    """Страница манги «по мотивам» (своя, процедурная): кадры с белыми полями, штриховка, чёрные заливки,
    линии скорости, силуэты и облачка речи. Ч/б с серым, бумага чуть желтоватая."""
    paper = C(0.86, 0.84, 0.78) * (0.92 + 0.12 * rng.random())
    pg = np.ones((ph, pw, 3), np.float32) * paper
    yy, xx = np.mgrid[0:ph, 0:pw].astype(np.float32)

    def fill(x0, y0, x1, y1):
        if x1 - x0 < 4 or y1 - y0 < 4:
            return
        w, h = x1 - x0, y1 - y0
        ly, lx = yy[y0:y1, x0:x1] - y0, xx[y0:y1, x0:x1] - x0
        kind = rng.choice(["hatch", "dark", "speed", "figure", "hatch", "dark"])
        if kind == "hatch":                                   # штриховка + серые пятна
            n = noise(w, h, max(2, w // 6), max(2, h // 6), rng, oct=3)
            v = np.where(n > 0.55, 0.15, np.where(((lx + ly) % 3 < 1) & (n > 0.4), 0.35, 0.9))
        elif kind == "dark":                                  # чёрная заливка с белыми прожилками
            n = noise(w, h, max(2, w // 4), max(2, h // 4), rng, oct=4)
            v = np.where(np.abs(n - 0.5) < 0.03, 0.85, 0.06)
        elif kind == "speed":                                 # линии скорости к центру
            cx, cy = w * rng.uniform(0.3, 0.7), h * rng.uniform(0.3, 0.7)
            ang = np.arctan2(ly - cy, lx - cx)
            v = np.where(np.sin(ang * rng.integers(18, 30)) > 0.6, 0.15, 0.92)
            r = np.hypot(lx - cx, ly - cy)
            v = np.where(r < min(w, h) * 0.25, 0.92, v)
        else:                                                 # силуэт: голова и плечи
            cx, cy = w * rng.uniform(0.3, 0.7), h * rng.uniform(0.35, 0.6)
            r = min(w, h) * rng.uniform(0.18, 0.3)
            body = ((lx - cx) / (r * 1.8)) ** 2 + ((ly - cy - r * 2.0) / (r * 1.3)) ** 2 < 1
            head = (lx - cx) ** 2 + (ly - cy) ** 2 < r * r
            hair = head & (ly < cy - r * 0.1)
            bg = np.where(noise(w, h, 3, 3, rng, oct=2) > 0.5, 0.8, 0.92)
            v = np.where(body, 0.08, bg)
            v = np.where(head, 0.88, v)
            v = np.where(hair, 0.1, v)
        pg[y0:y1, x0:x1] = paper * v[..., None]
        pg[y0, x0:x1] = 0.05                                  # рамка кадра
        pg[y1 - 1, x0:x1] = 0.05
        pg[y0:y1, x0] = 0.05
        pg[y0:y1, x1 - 1] = 0.05
        if rng.random() < 0.55 and w > 10 and h > 9:          # облачко речи
            bw, bh = rng.uniform(0.3, 0.55) * w, rng.uniform(0.25, 0.4) * h
            bx = x0 + rng.uniform(0.1, 0.9) * (w - bw) + bw / 2
            by = y0 + rng.uniform(0.1, 0.9) * (h - bh) + bh / 2
            e = ((xx - bx) / (bw / 2)) ** 2 + ((yy - by) / (bh / 2)) ** 2
            box = (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
            pg[(e >= 1) & (e < 1.35) & box] = 0.08
            pg[(e < 1) & box] = paper * 0.97
            for k in range(int(bh // 3)):                     # строчки текста
                ty = int(by - bh / 2 + 2 + k * 3)
                tx0, tx1 = int(bx - bw * 0.3), int(bx + bw * 0.3)
                if y0 < ty < y1 - 1:
                    pg[ty, max(tx0, x0 + 1):min(tx1, x1 - 1)] = paper * 0.45

    if rng.random() < 0.12:                                   # разворот-заливка на всю страницу
        fill(1, 1, pw - 1, ph - 1)
    else:
        rows = int(rng.integers(2, 4))
        cuts = sorted(rng.uniform(0.2, 0.8, rows - 1))
        ys = [1] + [int(c * ph) for c in cuts] + [ph - 1]
        for r in range(len(ys) - 1):
            xs = [1] + ([int(rng.uniform(0.3, 0.7) * pw)] if rng.random() < 0.5 else []) + [pw - 1]
            for c in range(len(xs) - 1):
                fill(xs[c] + 1, ys[r] + 1, xs[c + 1] - 1, ys[r + 1] - 1)
    return pg


def tex_south():
    """Стена напротив дивана: белая штукатурка, как у стены с дверью; у двери (левый край текстуры) — коллаж из страниц манги на левую половину стены,
    ряды к низу обрываются неровно, как на фото. 1024 x 512 на 3.88 x 2.5 м."""
    w, h = 1024, 512
    # прежняя основа (облезлая серая штукатурка) больше не рисуется, но её вызовы оставлены: они двигают общий
    # генератор R, и без них поменялись бы все текстуры после этой (стена с дверью, пол, плед, атлас...)
    _ = peeled(plaster(R, w, h, (0.76, 0.75, 0.70), streak=0.2, stains=0.3, crack=0.25), R, C(0.56, 0.54, 0.48), 16, 0.04)
    _ = floor_grime(h, w, R, 0.25, 0.45)
    # основа — как у стены с дверью (tex_east): белая штукатурка с бледными разводами, у потолка краска
    # облупилась до светлой шпаклёвки; масштаб пятен — тот же на метр стены. Свой генератор — R не трогаем.
    SR = np.random.default_rng(303)
    arr = plaster(SR, w, h, (0.78, 0.77, 0.72), streak=0.12, stains=0.08, crack=0.15)
    top = np.zeros((h, w), np.float32); top[:140] = 1
    top = blur(top[..., None], 16)[..., 0]
    patches = smoothstep(0.55, 0.62, noise(w, h, 13, 5, SR, oct=3)) * top
    under = C(0.86, 0.85, 0.80) * (0.94 + 0.1 * noise(w, h, 21, 8, SR))[..., None]
    arr = arr * (1 - patches[..., None]) + under * patches[..., None]
    rim = np.clip(patches - np.roll(patches, (3, 3), (0, 1)), 0, 1)
    arr *= (1 - rim * 0.18)[..., None]
    arr *= (1 - floor_grime(h, w, SR, 0.2, 0.4))[..., None]
    ppm_x, ppm_y = w / (X1 - X0), h / H                        # пикселей на метр
    PW, PH = 0.205, 0.285                                      # страница, м
    # 8 столбцов (~1.65 м) у самой двери, четыре полных ряда, ниже — неровный обрыв; правая половина стены пустая
    cols_in_row = [range(8)] * 4 + [range(7), [1, 2, 3, 5], [2, 6]]
    top = 2.45                                                 # верх коллажа от пола, м
    for r, cols in enumerate(cols_in_row):
        for c in cols:
            x_m = 0.35 + c * PW + RM.uniform(-0.012, 0.012)        # от угла с дверью — 0.35 м
            z_m = top - (r + 1) * PH + RM.uniform(-0.012, 0.012)
            x0, y0 = int(x_m * ppm_x), int((H - z_m - PH) * ppm_y)
            pw, ph = int(PW * ppm_x) - 1, int(PH * ppm_y) - 1
            pg = manga_page(pw, ph, RM)
            pg *= np.linspace(1.0, 0.94, ph, dtype=np.float32)[:, None, None]     # низ страницы чуть темнее
            arr[y0 + ph:y0 + ph + 2, x0 + 2:x0 + pw + 2] *= 0.7                      # тень под листом
            arr[y0:y0 + ph, x0 + pw:x0 + pw + 2] *= 0.8
            arr[y0:y0 + ph, x0:x0 + pw] = pg
    save("yr_south", finish(arr, 1.1, crisp=0.3))


def tex_east():
    """Стена с дверью: белая штукатурка, у потолка отвалилась; выключатель на 1.5 м у проёма, розетка под ним.
    Надписи маркером над столом — отдельная прозрачная наклейка (render_writing). Левый край текстуры — северный угол."""
    w, h = 512, 256
    # Как на фото: пятна и разводы бледные (сероватые, не бурые); у потолка краска облупилась до светлой,
    # почти белой шпаклёвки — сколы светлее стены, по краю лишь тонкая серая кромка.
    arr = plaster(R, w, h, (0.78, 0.77, 0.72), streak=0.12, stains=0.08, crack=0.15)
    top = np.zeros((h, w), np.float32); top[:70] = 1
    top = blur(top[..., None], 8)[..., 0]
    patches = smoothstep(0.55, 0.62, noise(w, h, 10, 5, R, oct=3)) * top
    under = C(0.86, 0.85, 0.80) * (0.94 + 0.1 * noise(w, h, 16, 8, R))[..., None]
    arr = arr * (1 - patches[..., None]) + under * patches[..., None]
    rim = np.clip(patches - np.roll(patches, (2, 2), (0, 1)), 0, 1)
    arr *= (1 - rim * 0.18)[..., None]
    ux = lambda y: int((Y1 - y) / (Y1 - Y0) * w)
    vy = lambda z: int((1 - z / H) * h)
    sx, sy = ux(2.10) - 6, vy(1.55) - 7                         # выключатель (y ≈ 2.07 м, h ≈ 1.5 м)
    arr[sy - 1:sy + 15, sx - 1:sx + 13] *= 0.6
    arr[sy:sy + 14, sx:sx + 12] = C(0.80, 0.78, 0.70)
    arr[sy + 2:sy + 12, sx + 3:sx + 9] = C(0.70, 0.68, 0.60)
    ox, oy = ux(2.24) - 5, vy(0.36) - 5                         # розетка под выключателем
    arr[oy - 1:oy + 11, ox - 1:ox + 11] *= 0.6
    arr[oy:oy + 10, ox:ox + 10] = C(0.78, 0.76, 0.68)
    arr[oy + 4:oy + 6, ox + 2:ox + 4] = C(0.1, 0.1, 0.1); arr[oy + 4:oy + 6, ox + 6:ox + 8] = C(0.1, 0.1, 0.1)
    arr *= (1 - floor_grime(h, w, R, 0.2, 0.4))[..., None]
    save("yr_east", finish(arr, 1.2))


# --- надписи маркером над столом (как на фото стены): рендер текста Blender'ом в прозрачную текстуру ---
WR_Y0, WR_Y1, WR_Z0, WR_Z1 = 2.21, 3.61, 0.88, 2.06          # где висит наклейка: y (с севера к двери), высота от пола
WR_PX = 420                                                    # пикселей на метр
FONT_HAND = r"C:\Windows\Fonts\segoepr.ttf"                     # Segoe Print — рукописный, с кириллицей
FONT_INK = r"C:\Windows\Fonts\Inkfree.ttf"                      # Ink Free — для латиницы
RED, GREY, BLACK = (0.55, 0.07, 0.04), (0.25, 0.25, 0.27), (0.06, 0.06, 0.07)
# (текст, x, y, высота букв — всё в пикселях фото стены 960x1280, поворот°, шрифт, цвет)
WRITING = [
    ("Началось", 175, 448, 20, 3, FONT_HAND, RED), ("element", 60, 528, 20, 12, FONT_INK, RED),
    ("/|\\", 180, 512, 26, 0, FONT_INK, RED), ("da?", 325, 498, 30, 0, FONT_INK, RED),
    ("tewiq", 430, 488, 48, 0, FONT_INK, RED), ("???", 265, 550, 20, 0, FONT_HAND, RED),
    ("67", 265, 603, 28, 0, FONT_HAND, RED), ("сука", 545, 598, 40, 0, FONT_HAND, RED),
    ("Это пиздец", 130, 628, 18, 2, FONT_HAND, RED), ("Ну прив", 270, 658, 24, 0, FONT_HAND, RED),
    ("RR", 510, 675, 30, 0, FONT_INK, RED), ("113 squad", 65, 693, 26, 0, FONT_INK, GREY),
    ("Гандон", 225, 708, 22, 0, FONT_HAND, RED), ("^ ^", 418, 712, 22, 0, FONT_INK, RED),
    ("ω", 425, 745, 26, 0, FONT_HAND, RED), ("Ты чё пидор?", 190, 750, 22, 0, FONT_HAND, RED),
    ("YYAA", 145, 786, 16, 0, FONT_INK, RED), ("секси айс", 222, 808, 16, 8, FONT_HAND, RED),
    ("<3", 385, 798, 22, 0, FONT_INK, RED), ("#2016", 455, 808, 26, -3, FONT_INK, RED),
    ("СВЭГ", 600, 775, 32, -5, FONT_HAND, RED), ("ПЯТЬТЫЩ", 655, 828, 28, -18, FONT_HAND, RED),
    ("9scarecrows", 365, 862, 22, -3, FONT_INK, RED), ("error nice///", 365, 902, 22, 0, FONT_INK, RED),
]
STROKES = [                                                  # линии маркером: (точки, цвет)
    ([(235, 382), (249, 365), (262, 382), (276, 365), (288, 382), (300, 365), (312, 382), (322, 368)], BLACK),   # зигзаг
    ([(690, 415), (690, 548)], RED), ([(668, 432), (676, 456)], RED),                                           # знак-руна
    ([(712, 425), (717, 450), (706, 460)], RED), ([(660, 458), (720, 520)], RED), ([(720, 458), (660, 520)], RED),
    ([(660, 520), (690, 548), (720, 520)], RED),
    ([(372, 572), (408, 572)], RED), ([(452, 572), (488, 572)], RED),                                           # глаза
    ([(372, 582), (372, 594), (408, 594), (408, 582), (372, 582)], RED),
    ([(452, 582), (452, 594), (488, 594), (488, 582), (452, 582)], RED),
    ([(382, 582), (382, 594)], RED), ([(392, 582), (392, 594)], RED), ([(462, 582), (462, 594)], RED), ([(472, 582), (472, 594)], RED),
    ([(395, 662), (440, 664)], RED), ([(452, 647), (446, 664)], RED),                                           # ухмылка «—/»
]
SMUDGES = []                                                   # размазанные пятна маркера (x, y, радиус)


def render_writing():
    """Отрисовать надписи в отдельной сцене (Workbench, плоский свет, прозрачный фон) → yr_writing.png (RGBA)."""
    W, Hh = WR_Y1 - WR_Y0, WR_Z1 - WR_Z0
    rx, ry = int(W * WR_PX), int(Hh * WR_PX)
    sc = bpy.data.scenes.new("Writing")
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'FLAT'
    sc.display.shading.color_type = 'MATERIAL'
    sc.display.render_aa = '16'
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = rx, ry, 100
    sc.view_settings.view_transform = 'Standard'
    sc.render.image_settings.color_mode = 'RGBA'
    cd = bpy.data.cameras.new("WrCam"); cd.type = 'ORTHO'; cd.ortho_scale = max(W, Hh)
    cam = bpy.data.objects.new("WrCam", cd); sc.collection.objects.link(cam)
    cam.location = (W / 2, Hh / 2, 5); sc.camera = cam
    # фото-пиксели → метры наклейки: x 40…900 → 0…W, y 340…910 → Hh…0
    sx = W / 860.0; sy = Hh / 570.0
    P = lambda px, py: ((px - 40) * sx, Hh - (py - 340) * sy)
    mats = {}

    def mt(col):
        if col not in mats:
            m = bpy.data.materials.new("Wr%d" % len(mats)); m.diffuse_color = (*col, 1.0); mats[col] = m
        return mats[col]

    fonts = {}
    for (txt, px, py, hpx, rot, fpath, col) in WRITING:
        if fpath not in fonts:
            fonts[fpath] = bpy.data.fonts.load(fpath)
        cu = bpy.data.curves.new("t", 'FONT')
        cu.body = txt; cu.font = fonts[fpath]; cu.size = hpx * sy * 1.45
        ob = bpy.data.objects.new("t", cu)
        ob.location = (*P(px, py), 0); ob.rotation_euler.z = math.radians(rot)
        ob.data.materials.append(mt(col))
        sc.collection.objects.link(ob)
    bm = B()
    wdt = 4.5 * sx
    for pts, col in STROKES:
        q = [Vector((*P(*p_), 0)) for p_ in pts]
        for a_, b_ in zip(q, q[1:]):
            d = (b_ - a_); n = Vector((-d.y, d.x, 0)).normalized() * wdt / 2
            e = d.normalized() * wdt / 2
            bm.poly([a_ - e - n, b_ + e - n, b_ + e + n, a_ - e + n], [(0, 0)] * 4, mt(col))
    for (px, py, r) in SMUDGES:                                # размазня — неровный многоугольник
        cx, cy = P(px, py)
        pts = [Vector((cx + math.cos(t) * r * sx * (0.6 + 0.6 * RM.random()), cy + math.sin(t) * r * sy * (0.4 + 0.4 * RM.random()), 0))
               for t in np.linspace(0, 2 * math.pi, 10, endpoint=False)]
        bm.poly(pts, [(0, 0)] * len(pts), mt(RED))
    bm.build("WrStrokes", sc.collection)
    out = os.path.join(ROOT, "assets", "textures", "yr_writing.png")
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True, scene=sc.name)
    # маркер: неровный нажим, местами прозрачнее, лёгкая мягкость
    img = bpy.data.images.load(out); img.reload()
    a = np.array(img.pixels[:], np.float32).reshape(ry, rx, 4)
    press = 0.78 + 0.22 * noise(rx, ry, rx // 6, ry // 6, RM, oct=3)
    a[..., 3] = np.clip(a[..., 3] * press * 1.35, 0, 1)
    a[..., :3] = blur(a[..., :3], 0.5, wrap=False)
    a[..., 3] = blur(a[..., 3:4], 0.6, wrap=False)[..., 0]
    img.pixels.foreach_set(a.ravel()); img.filepath_raw = out; img.file_format = 'PNG'; img.save()
    bpy.data.scenes.remove(sc)


def tex_floor_ceiling():
    """Ламинат (как на фото): светлый «дуб» с напечатанными волокнами, доски 1.3 x 0.2 м вразбежку, тёмные стыки,
    у стен грязнее. Потолок — ровная светлая побелка с бледными разводами."""
    FR = np.random.default_rng(303)
    w = h = 512                                                    # 2 x 2 м
    rows = 10
    rh = h / rows
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    row = (yy // rh).astype(int)
    shift = (FR.random(rows) * w).astype(np.float32)
    PL = 333.0                                                     # длина доски, px
    xs = (xx + shift[row]) % w
    plank = (xs // PL).astype(int) + row * 7
    tone = (0.88 + 0.22 * FR.random(200)).astype(np.float32)
    grain = noise(w, h, 3, 90, FR, oct=4)
    fine = noise(w, h, 6, 200, FR, oct=2)
    arr = np.ones((h, w, 3), np.float32) * C(0.74, 0.58, 0.40)
    arr *= tone[plank % 200][..., None]
    arr *= (0.86 + 0.22 * grain + 0.08 * fine)[..., None]
    knots = np.abs(np.sin((yy + grain * 40) * 0.9)) < 0.08
    arr[knots] *= 0.9
    fy = (yy % rh); fx = xs % PL
    arr[(fy < 1.2)] *= 0.55; arr[(fy >= 1.2) & (fy < 2.4)] *= 1.06
    arr[(fx < 1.5)] *= 0.6
    arr *= mottle(h, w, FR, 2, 0.12)[..., None]
    save("yr_laminate", finish(arr, 1.1, crisp=0.3))
    c = plaster(FR, 256, 256, (0.84, 0.82, 0.77), streak=0.0, stains=0.12, rough=0.03, crack=0.08)
    save("yr_ceiling", finish(c, 1.3))


def tex_blanket():
    """Плед (как на фото): ржаво-оранжевый ворсистый, по полю — тёмные и золотистые завитки-вензеля и крупные
    пионы (персиковые лепестки слоями, оливковые листья), в центре кремово-золотой медальон с букетом,
    по краю — «леопардовая» кайма с розетками. 512 x 512 на весь плед вместе со свесами."""
    s = 512
    BR = np.random.default_rng(304)
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    u = (xx - s / 2 + 0.5) / (s / 2); v = (yy - s / 2 + 0.5) / (s / 2)
    sq = np.maximum(np.abs(u), np.abs(v))
    arr = np.ones((s, s, 3), np.float32) * C(0.62, 0.28, 0.09)
    arr *= (0.85 + 0.3 * noise(s, s, 10, 10, BR, oct=3))[..., None]
    sc1 = np.abs(noise(s, s, 14, 14, BR, oct=2) - 0.5) < 0.022                     # тёмные вензеля
    sc2 = np.abs(noise(s, s, 11, 11, BR, oct=2) - 0.5) < 0.010                     # золотистые вензеля
    arr[sc1] = arr[sc1] * 0.55
    arr[sc2] = arr[sc2] * 0.4 + C(0.80, 0.52, 0.24) * 0.6

    def leafy(cx, cy, ang, L, W):
        ca, sa = math.cos(ang), math.sin(ang)
        lx = (xx - cx) * ca + (yy - cy) * sa; ly = -(xx - cx) * sa + (yy - cy) * ca
        m = ((lx - L / 2) / (L / 2)) ** 2 + (ly / (W / 2)) ** 2 < 1
        vein = m & (np.abs(ly) < 0.9)
        return m, vein

    def peony(cx, cy, r, light, dark):
        dx, dy = xx - cx, yy - cy
        rr = np.hypot(dx, dy); a = np.arctan2(dy, dx)
        edge = r * (0.86 + 0.10 * np.sin(a * 7 + cx) + 0.04 * np.sin(a * 13))
        m = rr < edge
        t = rr / r
        layers = 0.5 + 0.5 * np.cos(2 * np.pi * (t * 3.2 + 0.18 * np.sin(a * 6 + cy)))
        shade = np.clip(layers * (0.55 + 0.45 * t), 0, 1)
        col = light * (1 - shade[..., None] * 0.6) + dark * (shade[..., None] * 0.6)
        col = np.where((t < 0.22)[..., None], dark * 0.9, col)
        return m, col

    def bouquet(cx, cy, r, k_leaves=5):
        for k in range(k_leaves):
            ang = BR.uniform(0, 6.283)
            m, vein = leafy(cx + math.cos(ang) * r * 0.7, cy + math.sin(ang) * r * 0.7, ang, r * 1.1, r * 0.45)
            arr[m] = C(0.50, 0.52, 0.24) * (0.8 + 0.3 * BR.random())
            arr[vein] = C(0.30, 0.32, 0.12)
        m, col = peony(cx, cy, r, C(0.98, 0.76, 0.55), C(0.72, 0.30, 0.12))
        arr[m] = col[m]

    for (cx, cy) in ((70, 70), (442, 70), (70, 442), (442, 442), (256, 58), (256, 454), (58, 256), (454, 256),
                     (150, 170), (362, 170), (150, 342), (362, 342)):
        bouquet(cx + BR.integers(-8, 9), cy + BR.integers(-8, 9), 34 + BR.integers(0, 10), 5)
    # медальон: кремово-золотой овал с кольцами и букетом
    e = (u / 0.50) ** 2 + (v / 0.40) ** 2
    med = C(0.86, 0.72, 0.46) * (0.9 + 0.15 * noise(s, s, 20, 20, BR))[..., None]
    arr = np.where((e < 1.0)[..., None], med, arr)
    arr = np.where(((e > 0.88) & (e < 0.96))[..., None], C(0.50, 0.20, 0.08), arr)
    arr = np.where(((e > 0.74) & (e < 0.79))[..., None], C(0.72, 0.45, 0.20), arr)
    lace = (e < 0.74) & (np.abs(noise(s, s, 24, 24, BR, oct=2) - 0.5) < 0.03)
    arr[lace] *= 0.82
    bouquet(256, 256, 58, 8)
    for (cx, cy) in ((200, 238), (312, 238), (230, 300), (284, 300)):
        bouquet(cx, cy, 28, 3)
    # кайма «под леопарда»: розетки — тёмное кольцо вокруг рыжего пятна
    border = sq > 0.84
    cells = noise(s, s, 40, 40, BR, oct=1)
    ros = (cells > 0.60) & (cells < 0.68)
    core = cells >= 0.68
    leo = np.ones((s, s, 3), np.float32) * C(0.80, 0.58, 0.30)
    leo[ros] = C(0.22, 0.10, 0.04); leo[core] = C(0.62, 0.32, 0.10)
    arr = np.where(border[..., None], leo, arr)
    arr = np.where(((sq > 0.80) & (sq <= 0.84))[..., None], C(0.48, 0.18, 0.06), arr)
    arr *= (0.84 + 0.26 * noise(s, s, 128, 128, BR, oct=2))[..., None]               # ворс
    arr *= mottle(s, s, BR, 2, 0.10)[..., None]
    save("yr_blanket", finish(blur(arr, 0.7, wrap=False), 1.1, crisp=0.3))


def tex_fabric():
    """Обивка дивана и кресла (как на фото): бежевый велюр — пятна примятого ворса светлее/темнее, мелкий ворс."""
    FB = np.random.default_rng(305)
    s = 128
    arr = np.ones((s, s, 3), np.float32) * C(0.60, 0.52, 0.41)
    arr *= (0.86 + 0.22 * noise(s, s, 5, 5, FB, oct=3))[..., None]                  # примятый ворс
    arr *= (0.94 + 0.10 * noise(s, s, 64, 64, FB, oct=1))[..., None]
    arr *= (0.97 + 0.06 * FB.random((s, s)).astype(np.float32))[..., None]
    save("yr_fabric", finish(arr, 1.1, crisp=0.2))
    # кресло у окна (как на фото): тёмная серо-сиреневая обивка с крупными блёклыми цветами
    s_ = 64
    yy, xx = np.mgrid[0:s_, 0:s_].astype(np.float32)
    a = np.ones((s_, s_, 3), np.float32) * C(0.27, 0.25, 0.32)
    for (cx, cy, r) in ((14, 16, 9), (44, 12, 7), (30, 40, 10), (54, 46, 8), (8, 52, 7)):
        rr = np.hypot(xx - cx, yy - cy); ang = np.arctan2(yy - cy, xx - cx)
        petal = (rr < r * (0.7 + 0.3 * np.cos(ang * 5))) & (rr > r * 0.25)
        a = np.where(petal[..., None], C(0.45, 0.43, 0.52), a)
        a = np.where((rr <= r * 0.25)[..., None], C(0.22, 0.20, 0.26), a)
    a *= (0.85 + 0.25 * noise(s_, s_, 16, 16, np.random.default_rng(77), oct=2))[..., None]   # свой генератор
    save("yr_armchair", finish(a, 1.1))


def tex_window():
    """Окно в белой пластиковой раме: две створки, стекло полупрозрачное (вид за окном — отдельная модель)."""
    s = 128
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    g = (yy / s)[..., None]
    glass = C(0.02, 0.03, 0.07) * (1 - g) + C(0.12, 0.08, 0.07) * g
    house = (yy > 34) & (xx > 10) & (xx < 112)
    glass = np.where(house[..., None], C(0.035, 0.035, 0.045), glass)
    lit = np.zeros((s, s), np.float32)
    for wy in range(40, 124, 10):
        for wx in range(16, 108, 9):
            if R.random() < 0.10:                                          # редкие тусклые окна напротив
                lit[wy:wy + 4, wx:wx + 3] = 0.25 + 0.3 * R.random()
    glass = glass + lit[..., None] * C(0.85, 0.55, 0.28)
    glass *= (0.8 + 0.4 * noise(s, s, 6, 6, R))[..., None]
    frame = np.zeros((s, s), bool)
    frame[:8] = frame[-8:] = True; frame[:, :8] = frame[:, -8:] = True
    frame[:, 60:68] = True                                                # импост
    for (a, b_) in ((8, 60), (68, 120)):                                  # рамы створок
        frame[8:14, a:b_] = True; frame[-14:-8, a:b_] = True
        frame[8:-8, a:a + 5] = True; frame[8:-8, b_ - 5:b_] = True
    frame[58:74, 70:74] = True                                            # ручка — на правой створке у импоста, как на фото
    frame[18:28, 118:122] = True; frame[100:110, 118:122] = True          # петли правой створки
    white = C(0.80, 0.80, 0.76) * (0.85 + 0.2 * noise(s, s, 8, 8, R))[..., None]
    alb = np.where(frame[..., None], white, glass)
    alb[58:74, 70:74] = C(0.86, 0.84, 0.74)
    alb[18:28, 118:122] = C(0.55, 0.55, 0.53); alb[100:110, 118:122] = C(0.55, 0.55, 0.53)
    # Стекло прозрачное (за ним — 3D-вид из окна, tools/blender/build_window_view.py): чуть синеватое, с засохшими
    # каплями и потёками, как на фото, и грязью у нижнего края рамы. Случайности — свои, чтобы не сдвигать R.
    WR = np.random.default_rng(2526)
    alpha = np.full((s, s), 0.10, np.float32)
    tint = np.ones((s, s, 3), np.float32) * C(0.10, 0.11, 0.13)
    for _ in range(260):                                                  # капли
        cx, cy, r = WR.uniform(0, s), WR.uniform(0, s), WR.uniform(0.6, 1.8)
        d = np.hypot(xx - cx, yy - cy)
        m = np.clip(1 - d / r, 0, 1) * WR.uniform(0.15, 0.35)
        alpha = np.maximum(alpha, m)
    for _ in range(18):                                                   # потёки сверху вниз
        cx, y0 = WR.uniform(10, s - 10), WR.uniform(8, s * 0.6)
        ln = WR.uniform(10, 50)
        m = (np.abs(xx - cx - np.sin(yy * 0.3) * 0.6) < 0.7) & (yy > y0) & (yy < y0 + ln)
        alpha = np.where(m, np.maximum(alpha, 0.2), alpha)
    alpha += np.clip((yy - (s - 34)) / 20.0, 0, 1) * 0.18                   # грязь у нижнего края
    alpha *= 0.85 + 0.3 * noise(s, s, 8, 8, WR)
    tint = tint * (1 - alpha[..., None]) + C(0.55, 0.55, 0.56) * alpha[..., None]
    alb = np.where(frame[..., None], white, tint)
    alb[58:74, 70:74] = C(0.86, 0.84, 0.74)
    alb[18:28, 118:122] = C(0.55, 0.55, 0.53); alb[100:110, 118:122] = C(0.55, 0.55, 0.53)
    alb = finish(alb, 1.1, crisp=0.3)
    # Текстура больше не сохраняется: окно теперь отдельная 3D-модель (build_room_window.py). Расчёт оставлен,
    # чтобы случайности у следующих текстур не сдвинулись.


def save_rgba(name, rgb, alpha):
    """PNG с прозрачностью в assets/textures (tex_lib.save пишет только RGB)."""
    h, w, _ = rgb.shape
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, w, h, alpha=True)
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = np.clip(rgb, 0, 1)
    rgba[..., 3] = np.clip(alpha, 0, 1)
    img.pixels.foreach_set(rgba[::-1].ravel())
    path = os.path.join(ROOT, "assets", "textures", name + ".png")
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    img.filepath = path


def tex_screen():
    """Экран монитора. Выключен — чёрный; emission — рабочий стол 2010 года: синие обои, иконки,
    панель задач с круглой кнопкой «Пуск», открытый браузер с синей шапкой соцсети."""
    w, h = 128, 104
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    off = np.ones((h, w, 3), np.float32) * C(0.02, 0.022, 0.028)
    off += (np.clip(1 - np.abs((xx - yy * 1.2) - 30) / 30, 0, 1) * 0.03)[..., None]   # блик на стекле
    save("yr_screen", off)
    g = (yy / h)[..., None]
    d = C(0.12, 0.36, 0.70) * (1 - g) + C(0.02, 0.10, 0.32) * g
    swoosh = np.exp(-((yy - (70 - 0.004 * (xx - 64) ** 2)) / 5) ** 2)
    d = d + swoosh[..., None] * C(0.25, 0.45, 0.55)
    d[h - 9:] = C(0.07, 0.11, 0.17)                                       # панель задач
    d[h - 9:h - 8] = C(0.25, 0.35, 0.45)
    orb = (xx - 6) ** 2 + (yy - (h - 4.5)) ** 2 < 14
    d = np.where(orb[..., None], C(0.25, 0.65, 0.55), d)
    for i, bx in enumerate((14, 32, 50)):                                 # кнопки окон
        d[h - 8:h - 1, bx:bx + 16] = C(0.20, 0.28, 0.38) if i == 0 else C(0.12, 0.18, 0.26)
    d[h - 7:h - 3, w - 18:w - 3] = C(0.55, 0.60, 0.65)                    # часы
    cols = (C(0.85, 0.75, 0.30), C(0.30, 0.55, 0.85), C(0.80, 0.80, 0.80), C(0.35, 0.70, 0.35), C(0.85, 0.35, 0.25))
    for i, c in enumerate(cols):                                          # иконки
        y0 = 4 + i * 16
        d[y0:y0 + 8, 5:13] = c
        d[y0 + 10:y0 + 11, 3:15] = C(0.85, 0.88, 0.92)
    x0, y0, x1, y1 = 26, 6, 124, 84                                       # окно браузера
    d[y0:y1, x0:x1] = C(0.92, 0.92, 0.90)
    d[y0:y0 + 6, x0:x1] = C(0.55, 0.70, 0.86)
    d[y0 + 1:y0 + 5, x1 - 6:x1 - 1] = C(0.80, 0.25, 0.20)
    d[y0 + 7:y0 + 10, x0 + 2:x1 - 2] = C(0.98, 0.98, 0.98)                # адресная строка
    d[y0 + 12:y0 + 19, x0:x1] = C(0.30, 0.44, 0.62)                       # шапка сайта
    d[y0 + 14:y0 + 17, x0 + 4:x0 + 28] = C(0.92, 0.94, 0.98)
    d[y0 + 23:y0 + 43, x0 + 4:x0 + 22] = C(0.55, 0.58, 0.62)              # аватарка
    for k in range(9):                                                    # строки текста
        L = int(R.integers(30, 70))
        d[y0 + 24 + k * 6:y0 + 26 + k * 6, x0 + 28:x0 + 28 + L] = C(0.45, 0.48, 0.55)
    d[y0 + 48:y0 + 52, x0 + 4:x0 + 22] = C(0.30, 0.44, 0.62)
    d[y0 + 56:y0 + 74, x0 + 4:x0 + 22] = C(0.80, 0.82, 0.86)
    save("yr_screen_emission", np.clip(d, 0, 1).astype(np.float32))


# --- атлас мелочей 256x256: прямоугольники (x0, y0, x1, y1) в пикселях, начало сверху-слева ---
A = {
    "black": (0, 0, 64, 64), "tower_f": (64, 0, 96, 72), "tower_s": (96, 0, 160, 72), "speaker": (160, 0, 192, 48),
    "cloth": (192, 32, 256, 64),
    "keyb": (0, 64, 128, 104), "drawer": (0, 104, 64, 168), "wood": (64, 104, 128, 168), "pot": (128, 104, 160, 136),
    "leaf": (160, 104, 192, 136), "picture": (192, 104, 256, 168), "mug": (0, 168, 32, 200), "bottle": (32, 168, 64, 200),
    "book": (64, 168, 128, 200), "clothes": (128, 168, 192, 232), "brass": (224, 168, 256, 200),
    "door": (0, 200, 32, 256), "mousepad": (32, 200, 64, 232), "white": (64, 200, 128, 232), "pillow": (128, 232, 160, 256),
    "soil": (192, 200, 224, 232), "cap": (224, 200, 256, 232),
    "plush": (128, 72, 160, 104), "bead": (160, 72, 192, 104),
}


def CLQ(q):
    """Четверть куска «clothes»: 0 — толстовка, 1 — джинса, 2 — трикотаж, 3 — куртка."""
    x0, y0, x1, y1 = A["clothes"]
    xa, ya = x0 + (q % 2) * 32, y0 + (q // 2) * 32
    return (xa / 256, 1 - (ya + 32) / 256, (xa + 32) / 256, 1 - ya / 256)


def RC(name):
    x0, y0, x1, y1 = A[name]
    return (x0 / 256, 1 - y1 / 256, x1 / 256, 1 - y0 / 256)


def tex_atlas():
    a = np.zeros((256, 256, 3), np.float32) + 0.2

    def put(name, arr):
        x0, y0, x1, y1 = A[name]
        a[y0:y1, x0:x1] = arr

    def flat(name, col, amp=0.25, cells=6):
        x0, y0, x1, y1 = A[name]
        w, h = x1 - x0, y1 - y0
        put(name, np.ones((h, w, 3), np.float32) * C(*col) * (1 - amp / 2 + amp * noise(w, h, cells, cells, R))[..., None])

    flat("black", (0.07, 0.07, 0.075), 0.3)
    # корпус: тёмно-серый, DVD-привод, заглушка, кардридер, кнопка, синий диод, USB, решётка
    f = np.ones((72, 32, 3), np.float32) * C(0.12, 0.12, 0.13) * (0.9 + 0.2 * noise(32, 72, 4, 8, R))[..., None]
    f[4:14, 3:29] = C(0.52, 0.53, 0.55); f[9:10, 5:27] = C(0.2, 0.2, 0.22); f[11:13, 24:27] = C(0.3, 0.3, 0.32)
    f[16:26, 3:29] = C(0.09, 0.09, 0.10); f[16:17, 3:29] = C(0.2, 0.2, 0.22)
    f[29:33, 6:26] = C(0.05, 0.05, 0.05)
    yy, xx = np.mgrid[0:72, 0:32]
    f[((xx - 16) ** 2 + (yy - 42) ** 2) < 16] = C(0.62, 0.63, 0.66)
    f[49:51, 15:17] = C(0.2, 0.45, 1.0)
    f[54:57, 9:13] = C(0.03, 0.03, 0.03); f[54:57, 19:23] = C(0.03, 0.03, 0.03)
    f[60:70, 3:29] *= np.where(((xx[60:70, 3:29] + yy[60:70, 3:29]) % 3 == 0)[..., None], 0.4, 1.0)
    f[:1] *= 0.5; f[-1:] *= 0.5; f[:, :1] *= 0.5; f[:, -1:] *= 0.5
    put("tower_f", f)
    s_ = np.ones((72, 64, 3), np.float32) * C(0.10, 0.10, 0.11) * (0.9 + 0.2 * noise(64, 72, 6, 6, R))[..., None]
    yy, xx = np.mgrid[0:72, 0:64]
    vent = (((xx - 32) ** 2 + (yy - 26) ** 2) < 144) & ((xx % 3 == 0) & (yy % 3 == 0))
    s_[vent] = C(0.02, 0.02, 0.02)
    put("tower_s", s_)
    sp = np.ones((48, 32, 3), np.float32) * C(0.08, 0.08, 0.08)
    yy, xx = np.mgrid[0:48, 0:32]
    r1 = np.sqrt((xx - 16) ** 2 + (yy - 31) ** 2); r2 = np.sqrt((xx - 16) ** 2 + (yy - 11) ** 2)
    sp[r1 < 12] = C(0.45, 0.45, 0.47); sp[r1 < 10.5] = C(0.13, 0.13, 0.14); sp[r1 < 3] = C(0.25, 0.25, 0.27)
    sp[r2 < 5] = C(0.45, 0.45, 0.47); sp[r2 < 3.5] = C(0.16, 0.16, 0.17)
    put("speaker", sp)
    yy, xx = np.mgrid[0:32, 0:64]
    put("cloth", C(0.80, 0.79, 0.74) * (0.88 + 0.12 * np.sin(xx / 3.0 + noise(64, 32, 4, 4, R) * 4))[..., None])
    # клавиатура: чёрная, серые клавиши
    kb = np.ones((40, 128, 3), np.float32) * C(0.05, 0.05, 0.05)
    for r in range(6):
        y0 = 3 + r * 6
        x = 3
        while x < 92:
            kw = 5 if not (r == 5 and 28 < x < 60) else 30
            if r == 5 and 28 < x < 60:
                kb[y0:y0 + 5, 30:60] = C(0.17, 0.17, 0.18); x = 61; continue
            kb[y0:y0 + 5, x:x + kw] = C(0.17, 0.17, 0.18)
            kb[y0 + 1:y0 + 2, x + 1:x + 2] = C(0.6, 0.6, 0.6)
            x += kw + 1
        for x in range(98, 124, 6):
            kb[y0:y0 + 5, x:x + 5] = C(0.17, 0.17, 0.18)
    put("keyb", kb)
    # комод (как на фото): светлый рыже-коричневый шпон «под ольху», четыре ящика с узкими ручками
    wd = np.ones((64, 64, 3), np.float32) * C(0.56, 0.31, 0.14) * (0.75 + 0.5 * noise(64, 64, 2, 16, R, oct=3))[..., None]
    put("wood", wd.copy())
    for k in (0, 16, 32, 48):
        wd[k:k + 2] *= 0.35
        wd[k + 7:k + 9, 24:40] = C(0.35, 0.22, 0.12)
    wd[:, :2] *= 0.5; wd[:, -2:] *= 0.5
    put("drawer", wd)
    flat("pot", (0.80, 0.37, 0.08), 0.2)
    lf = np.ones((32, 32, 3), np.float32) * C(0.10, 0.30, 0.09) * (0.8 + 0.4 * noise(32, 32, 4, 4, R))[..., None]
    lf[:, 15:17] = C(0.25, 0.45, 0.20)
    for k in range(2, 32, 6):
        lf[k, 4:28] *= 1.25
    put("leaf", lf)
    pic = np.ones((64, 64, 3), np.float32) * C(0.60, 0.48, 0.22) * (0.8 + 0.4 * noise(64, 64, 8, 8, R))[..., None]
    yy, xx = np.mgrid[0:52, 0:52]
    inner = C(0.15, 0.20, 0.30) * (1 - (yy / 52)[..., None]) + C(0.10, 0.14, 0.08) * (yy / 52)[..., None]
    inner = np.where((((xx - 26) / 9) ** 2 + ((yy - 24) / 14) ** 2 < 1)[..., None], C(0.45, 0.30, 0.18), inner)
    inner = np.where((((xx - 26) / 7) ** 2 + ((yy - 13) / 6) ** 2 < 1)[..., None], C(0.75, 0.62, 0.30), inner)
    pic[6:58, 6:58] = inner
    put("picture", pic)
    mg = np.ones((32, 32, 3), np.float32) * C(0.86, 0.85, 0.82)
    yy, xx = np.mgrid[0:32, 0:32]
    heart = ((xx - 16) / 6) ** 2 + ((yy - 16 - np.abs(xx - 16) * 0.6) / 6) ** 2 < 1
    mg[heart] = C(0.85, 0.35, 0.45); put("mug", mg)
    bt = np.ones((32, 32, 3), np.float32) * C(0.55, 0.70, 0.80) * (0.8 + 0.4 * noise(32, 32, 2, 6, R))[..., None]
    bt[12:22] = C(0.85, 0.88, 0.92); bt[15:18, 4:28] = C(0.15, 0.35, 0.75); bt[19:20, 8:24] = C(0.75, 0.15, 0.12)
    put("bottle", bt)
    bo = np.ones((32, 64, 3), np.float32) * C(0.55, 0.08, 0.06) * (0.85 + 0.3 * noise(64, 32, 6, 4, R))[..., None]
    bo[8:12, 10:50] = C(0.85, 0.70, 0.30); bo[16:19, 14:40] = C(0.85, 0.70, 0.30); bo[:, :3] *= 0.6
    put("book", bo)
    # одежда — четыре куска 32x32: чёрная толстовка (красный шнурок), джинса, серый трикотаж, тёмно-синяя куртка;
    # по каждому — тени складок
    cl = np.zeros((64, 64, 3), np.float32)
    yy, xx = np.mgrid[0:32, 0:32].astype(np.float32)
    for q, (col, kind) in enumerate(((C(0.06, 0.06, 0.07), "hood"), (C(0.25, 0.34, 0.50), "denim"),
                                     (C(0.42, 0.42, 0.44), "knit"), (C(0.11, 0.13, 0.20), "jacket"))):
        sw_ = np.ones((32, 32, 3), np.float32) * col
        folds = 0.82 + 0.3 * noise(32, 32, 3, 3, R, oct=2)
        sw_ *= folds[..., None]
        if kind == "denim":
            sw_ *= (0.9 + 0.12 * ((xx + yy) % 3 < 1))[..., None]
            sw_[:, 14:15] = C(0.70, 0.55, 0.25)                         # шов
        elif kind == "knit":
            sw_ *= (0.9 + 0.12 * (yy % 2 < 1))[..., None]
        elif kind == "hood":
            sw_[np.abs(xx - 10 - 3 * np.sin(yy / 4)) < 0.5] = C(0.45, 0.08, 0.07)
        else:
            sw_[16:17] = C(0.5, 0.5, 0.52)                               # молния
        y_, x_ = (q // 2) * 32, (q % 2) * 32
        cl[y_:y_ + 32, x_:x_ + 32] = sw_
    put("clothes", cl)
    flat("brass", (0.58, 0.44, 0.20), 0.3)
    dr = np.ones((56, 32, 3), np.float32) * C(0.80, 0.79, 0.74) * (0.9 + 0.15 * noise(32, 56, 4, 6, R))[..., None]
    dr[4:24, 4:28] = C(0.62, 0.54, 0.40) * (0.85 + 0.25 * np.sin(np.arange(24)[None, :] / 1.5))[..., None]   # стекло со шторкой
    dr[30:52, 4:28] *= 0.9; dr[30:31, 4:28] *= 0.8; dr[51:52, 4:28] *= 1.1
    dr[26:29, 25:30] = C(0.30, 0.28, 0.25)                                       # ручка
    dr[:1] *= 0.6; dr[:, :1] *= 0.6; dr[:, -1:] *= 0.6
    put("door", dr)
    mp = np.ones((32, 32, 3), np.float32) * C(0.06, 0.05, 0.05)
    yy, xx = np.mgrid[0:32, 0:32]
    mp[np.abs(yy - 20 - 6 * np.sin(xx / 6)) < 1.2] = C(0.65, 0.10, 0.08)
    mp[np.abs(yy - 10 - 4 * np.sin(xx / 4 + 1)) < 0.8] = C(0.55, 0.08, 0.06)
    put("mousepad", mp)
    flat("white", (0.80, 0.80, 0.77), 0.15)
    pl = np.ones((24, 32, 3), np.float32) * C(0.40, 0.43, 0.52) * (0.85 + 0.3 * noise(32, 24, 4, 4, R))[..., None]
    put("pillow", pl)                                                                             # серо-голубая подушка
    flat("soil", (0.10, 0.07, 0.05), 0.4)
    flat("cap", (0.15, 0.35, 0.75), 0.2)
    pl = np.ones((32, 32, 3), np.float32) * C(0.78, 0.12, 0.10) * (0.7 + 0.6 * R.random((32, 32, 1)).astype(np.float32))
    pl[12:17, 8:12] = C(0.03, 0.03, 0.03); pl[12:17, 20:24] = C(0.03, 0.03, 0.03)               # мягкая игрушка: глазки
    put("plush", pl)
    bd = np.ones((32, 32, 3), np.float32) * C(0.08, 0.50, 0.22)
    bd[4:12, 4:12] = C(0.45, 0.85, 0.55)                                                          # бусина гирлянды: блик
    put("bead", bd)
    save("yr_atlas", finish(a, 1.0, crisp=0.3))


# =====================================================================================
#  Помощники геометрии
# =====================================================================================
SPEC = {'+X': (1, 3, 7, 5), '-X': (2, 0, 4, 6), '+Y': (3, 2, 6, 7), '-Y': (0, 1, 5, 4), '+Z': (4, 5, 7, 6), '-Z': (0, 2, 3, 1)}


def obox(b, c, size, m, rect, yaw=0.0, pitch=0.0, faces=None, skip=()):
    """Повёрнутый ящик: центр c, размер size, поворот yaw (вокруг Z) и pitch (наклон вокруг X), градусы.
    faces: {'+Z': (mat, rect), ...} — переопределить отдельные грани; skip — грани, которых нет."""
    rot = Euler((math.radians(pitch), 0, math.radians(yaw)), 'XYZ').to_matrix()
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    cc = Vector(c)
    pts = [cc + rot @ Vector((hx if i & 1 else -hx, hy if i & 2 else -hy, hz if i & 4 else -hz)) for i in range(8)]
    for k, idx in SPEC.items():
        if k in skip:
            continue
        mm, (u0, v0, u1, v1) = (faces or {}).get(k, (m, rect))
        b.poly([pts[i] for i in idx], [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], mm)


def abox(b, mn, mx, m, rect, faces=None, skip=()):
    """Ящик по углам (без поворота) с развёрткой каждой грани в прямоугольник атласа."""
    c = [(mn[i] + mx[i]) / 2 for i in range(3)]
    obox(b, c, [mx[i] - mn[i] for i in range(3)], m, rect, faces=faces, skip=skip)


def cylr(b, p0, p1, r0, r1, m, rect, segs=8, caps=True):
    """Цилиндр/конус с развёрткой в прямоугольник атласа."""
    p0, p1 = Vector(p0), Vector(p1)
    ax = (p1 - p0).normalized()
    t = Vector((1, 0, 0)) if abs(ax.x) < 0.9 else Vector((0, 1, 0))
    u = ax.cross(t).normalized(); w = ax.cross(u)
    ring = lambda p, r, a: p + (u * math.cos(a) + w * math.sin(a)) * r
    u0, v0, u1, v1 = rect
    for i in range(segs):
        a0 = 2 * math.pi * i / segs; a1 = 2 * math.pi * (i + 1) / segs
        ua, ub = u0 + (u1 - u0) * i / segs, u0 + (u1 - u0) * (i + 1) / segs
        b.poly([ring(p0, r0, a0), ring(p0, r0, a1), ring(p1, r1, a1), ring(p1, r1, a0)], [(ua, v0), (ub, v0), (ub, v1), (ua, v1)], m)
    if caps:
        c = ((u0 + u1) / 2, (v0 + v1) / 2)
        if r1 > 1e-4:
            b.poly([ring(p1, r1, 2 * math.pi * i / segs) for i in range(segs)], [c] * segs, m)
        if r0 > 1e-4:
            b.poly([ring(p0, r0, -2 * math.pi * i / segs) for i in range(segs)], [c] * segs, m)


def leaf(b, base, yaw, tilt, L, W, m, rect):
    """Двусторонний лист спатифиллума: черешок, широкая ланцетная пластина, кончик свисает (градусы)."""
    y, t_ = math.radians(yaw), math.radians(tilt)
    base = Vector(base)
    d = Vector((math.cos(y) * math.sin(t_), math.sin(y) * math.sin(t_), math.cos(t_)))
    side = Vector((-math.sin(y), math.cos(y), 0))
    u0, v0, u1, v1 = rect
    um = (u0 + u1) / 2
    prof = [(0.0, 0.0), (0.35, 0.04), (0.45, 0.42), (0.62, 0.50), (0.80, 0.34), (1.0, 0.0)]   # (доля длины, полуширина)
    spine = [base + d * (L * f) - Vector((0, 0, L * 0.45 * math.sin(t_) * f * f)) for f, _ in prof]
    for k in range(len(prof) - 1):
        (fa, wa), (fb, wb) = prof[k], prof[k + 1]
        a0, a1 = spine[k], spine[k + 1]
        pts = [a0 - side * (W * wa), a1 - side * (W * wb), a1 + side * (W * wb), a0 + side * (W * wa)]
        va, vb = v0 + (v1 - v0) * fa, v0 + (v1 - v0) * fb
        uvs = [(um - (um - u0) * wa * 2, va), (um - (um - u0) * wb * 2, vb), (um + (u1 - um) * wb * 2, vb), (um + (u1 - um) * wa * 2, va)]
        b.poly(pts, uvs, m)
        b.poly(pts[::-1], uvs[::-1], m)


def plant(b, base, n, L, M, rng, spread=50):
    """Цветок в горшке: горшок, земля, n листьев."""
    x, y, z = base
    cylr(b, (x, y, z), (x, y, z + 0.17), 0.075, 0.1, M["atlas"], RC("pot"), segs=8, caps=False)
    cylr(b, (x, y, z + 0.15), (x, y, z + 0.155), 0.095, 0.095, M["atlas"], RC("soil"), segs=8)
    for i in range(n):
        leaf(b, (x, y, z + 0.15), i * 360 / n + rng.uniform(-15, 15), rng.uniform(15, spread), L * rng.uniform(0.7, 1.1),
             L * 0.32, M["atlas"], RC("leaf"))


class SB(B):
    """Мягкие формы с общими вершинами — после сборки затеняются гладко (обивка, плед, одежда)."""

    def build(self, name, coll):
        ob = super().build(name, coll)
        ob.data.shade_smooth()
        return ob


def _axis_coords(h, rr, k):
    """Координаты сетки вдоль оси: частые у краёв (там скругление), k равных шагов в середине."""
    if rr < 1e-4:
        return list(np.linspace(-h, h, k + 1))
    inner = list(np.linspace(-h + rr, h - rr, k + 1))
    return [-h, -h + rr * 0.45] + inner + [h - rr * 0.45, h]


def _rot(pitch, roll, yaw):
    return Euler((math.radians(pitch), math.radians(roll), math.radians(yaw)), 'XYZ').to_matrix()


def soft(sb, c, size, m, rect, r=0.05, n=(3, 3, 2), amp=0.0, rng=None, yaw=0.0, pitch=0.0, roll=0.0,
         sag=0.0, taper=1.0, bottom=False, freq=7.0, pivot=None):
    """Скруглённый ящик (обивка, подушки, одежда): радиус r, лёгкая «бугристость» amp, провис верха sag,
    taper — сужение к верху. pivot — точка, вокруг которой поворачивать (по умолчанию центр)."""
    h = [size[0] / 2, size[1] / 2, size[2] / 2]
    rr = min(r, min(h) * 0.98)
    ph = [rng.uniform(0, 6.283) for _ in range(6)] if rng else [0.0] * 6
    rot = _rot(pitch, roll, yaw)
    cc = Vector(c)
    pv = Vector(pivot) if pivot is not None else cc
    axes = [_axis_coords(h[i], rr, n[i]) for i in range(3)]
    E = [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
    FACES = [(0, 1, 1, 2, 1), (0, -1, 1, 2, -1), (1, 1, 0, 2, -1), (1, -1, 0, 2, 1), (2, 1, 0, 1, 1), (2, -1, 0, 1, -1)]
    idx = {}
    u0, v0, u1, v1 = rect

    def vert(p):
        key = (round(p.x, 5), round(p.y, 5), round(p.z, 5))
        if key in idx:
            return idx[key]
        q = Vector(p)
        t = (q.z + h[2]) / (2 * h[2])
        s_ = 1 + (taper - 1) * t
        q.x *= s_; q.y *= s_
        hx, hy = h[0] * s_, h[1] * s_
        inner = Vector((max(-hx + rr, min(hx - rr, q.x)), max(-hy + rr, min(hy - rr, q.y)), max(-h[2] + rr, min(h[2] - rr, q.z))))
        d = q - inner
        nrm = d.normalized() if d.length > 1e-7 else Vector((0, 0, 1))
        q = inner + nrm * rr if d.length > 1e-7 else q
        if sag and q.z > 0:
            q.z -= sag * (1 - (q.x / hx) ** 2) * (1 - (q.y / hy) ** 2) * (q.z / h[2])
        if amp:
            w_ = (math.sin(q.x * freq + ph[0]) * math.sin(q.y * freq * 1.3 + ph[1]) +
                  0.5 * math.sin((q.x + q.z) * freq * 2.1 + ph[2]) * math.sin(q.y * freq * 1.7 + ph[3]) +
                  0.3 * math.sin(q.z * freq * 1.5 + ph[4]))
            q = q + nrm * (amp * w_)
        world = pv + rot @ (cc + q - pv)
        idx[key] = len(sb.v)
        sb.v.append(tuple(world))
        return idx[key]

    for (a, s, ua, va, us) in FACES:
        if a == 2 and s < 0 and not bottom:
            continue
        A, V_ = axes[ua], axes[va]
        if us < 0:
            A = A[::-1]
        V_ = V_ if not (a == 2 and s < 0) else V_[::-1]
        grid = []
        for vv in V_:
            row = []
            for uu in A:
                p = Vector((0, 0, 0)); p[a] = s * h[a]; p[ua] = uu; p[va] = vv
                row.append(vert(p))
            grid.append(row)
        nu, nv = len(A) - 1, len(V_) - 1
        su = [(uu - A[0]) / (A[-1] - A[0]) for uu in A]
        sv = [(vv - V_[0]) / (V_[-1] - V_[0]) for vv in V_]
        mi = sb._m(m)
        for j in range(nv):
            for i in range(nu):
                f = (grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i])
                sb.f.append(f)
                sb.uv.append([(u0 + (u1 - u0) * su[i], v0 + (v1 - v0) * sv[j]), (u0 + (u1 - u0) * su[i + 1], v0 + (v1 - v0) * sv[j]),
                              (u0 + (u1 - u0) * su[i + 1], v0 + (v1 - v0) * sv[j + 1]), (u0 + (u1 - u0) * su[i], v0 + (v1 - v0) * sv[j + 1])])
                sb.mi.append(mi)


def drape(sb, x0, x1, y0, y1, zt, hang, m, rect, rng, n=(10, 12), nh=4, amp=0.015, edge=0.05, zfloor=None, fold=0.03, bumps=()):
    """Ткань, наброшенная на прямоугольник x0..x1, y0..y1 на высоте zt и свисающая по сторонам.
    hang = {'-X':, '+X':, '-Y':, '+Y':} — длина свеса, число или функция от координаты вдоль края.
    Складки: бугры сверху (amp) и вертикальные волны на свесе (fold)."""
    zfloor = Z + 0.012 if zfloor is None else zfloor
    hv = lambda k, t: (hang.get(k, 0.0)(t) if callable(hang.get(k, 0.0)) else hang.get(k, 0.0))
    ph = [rng.uniform(0, 6.283) for _ in range(6)]

    def seg(a, b_, k):
        return list(np.linspace(a, b_, k + 1))
    # параметры: доля по свесу (-1..0), по верху (0..1), по свесу (1..2)
    us = [-1 + t for t in seg(0, 1, nh)[:-1]] + seg(0, 1, n[0]) + [1 + t for t in seg(0, 1, nh)[1:]]
    vs = [-1 + t for t in seg(0, 1, nh)[:-1]] + seg(0, 1, n[1]) + [1 + t for t in seg(0, 1, nh)[1:]]
    W, D = x1 - x0, y1 - y0
    arc = edge * math.pi / 2
    smp = lambda k, a, b_: max(hv(k, a + (b_ - a) * q) for q in np.linspace(0, 1, 9))
    hmx = (smp('-X', y0, y1), smp('+X', y0, y1), smp('-Y', x0, x1), smp('+Y', x0, x1))   # для развёртки UV
    pos, uvp = {}, {}
    for j, v in enumerate(vs):
        for i, u in enumerate(us):
            px = x0 + W * min(max(u, 0), 1); py = y0 + D * min(max(v, 0), 1)
            ox = -hv('-X', py) * (-u) if u < 0 else (hv('+X', py) * (u - 1) if u > 1 else 0.0)
            oy = -hv('-Y', px) * (-v) if v < 0 else (hv('+Y', px) * (v - 1) if v > 1 else 0.0)
            dist = math.hypot(ox, oy)
            z = zt + amp * (math.sin(px * 5.1 + ph[0]) * math.sin(py * 4.3 + ph[1]) + 0.6 * math.sin(px * 11 + py * 7 + ph[2]))
            for (bx, by, br, bh) in bumps:                             # комья под тканью
                z += bh * math.exp(-((px - bx) ** 2 + (py - by) ** 2) / (br * br))
            x, y = px, py
            if dist > 1e-6:
                dx, dy = ox / dist, oy / dist
                if dist < arc:
                    a_ = dist / edge
                    hor, dz = edge * math.sin(a_), edge * (1 - math.cos(a_))
                else:
                    hor, dz = edge + (dist - arc) * 0.06, edge + (dist - arc)
                zz = zt - dz
                if zz < zfloor:                                        # легла на пол — тянется дальше по полу
                    hor += (zfloor - zz); zz = zfloor
                tang = (py if abs(dx) > abs(dy) else px)
                wv = fold * math.sin(tang * 17 + ph[3]) * min(1, dist / 0.2) + fold * 0.5 * math.sin(tang * 37 + ph[4]) * min(1, dist / 0.3)
                x, y, z = px + dx * (hor + wv), py + dy * (hor + wv), zz + (z - zt) * 0.3
            pos[(i, j)] = (x, y, z)
            uvp[(i, j)] = ((W * min(max(u, 0), 1) + ox + hmx[0]) / (W + hmx[0] + hmx[1]),
                           (D * min(max(v, 0), 1) + oy + hmx[2]) / (D + hmx[2] + hmx[3]))
    base = len(sb.v)
    NI = len(us)
    for j in range(len(vs)):
        for i in range(NI):
            sb.v.append(pos[(i, j)])
    u0, v0, u1, v1 = rect
    mi = sb._m(m)
    for j in range(len(vs) - 1):
        for i in range(NI - 1):
            ids = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            sb.f.append(tuple(base + b_ * NI + a for (a, b_) in ids))
            sb.uv.append([(u0 + (u1 - u0) * uvp[k][0], v0 + (v1 - v0) * uvp[k][1]) for k in ids])
            sb.mi.append(mi)


# =====================================================================================
#  Предметы: каждый — отдельная модель assets/models/yurchik_room/<имя>.gltf
# =====================================================================================
ITEM_DIR = os.path.join(OUT, "yurchik_room")
ANCHOR_TOP = ("chandelier",)               # висит на потолке — точка опоры сверху, у остальных — снизу по центру


def camel(item):
    return "".join(w.capitalize() for w in item.split("_"))


class Items:
    """Предметы комнаты. I("sofa", "soft") — сетка нужного вида для предмета (создаётся при первом обращении):
    solid  — жёсткое, Godot сделает коллизию по сетке (ps2_import.gd);
    detail — мелочь без коллизии (…_nocol);
    soft   — мягкое с гладким затенением, без коллизии (…Soft_nocol);
    col    — невидимые простые ящики-коллизии (…Col-colonly).
    name — своё имя объекта (игра ищет PCScreen_nocol, LightSwitchKey_nocol)."""
    KINDS = {"solid": (B, ""), "detail": (B, "_nocol"), "soft": (SB, "Soft_nocol"), "col": (B, "Col-colonly")}

    def __init__(self):
        self.items = {}

    def _it(self, item):
        return self.items.setdefault(item, {"parts": {}, "extra": []})

    def __call__(self, item, kind="detail", name=None):
        parts = self._it(item)["parts"]
        key = name or kind
        if key not in parts:
            parts[key] = (self.KINDS[kind][0](), name or camel(item) + self.KINDS[kind][1])
        return parts[key][0]

    def extra(self, item, ob):
        """Готовый объект со своей точкой вращения (клавиша выключателя)."""
        self._it(item)["extra"].append(ob)


def export_items(I, coll):
    """Каждый предмет: своя коллекция yr_<имя> в Blender, точка опоры у основания, свой файл .gltf.
    Возвращает {предмет: позиция в Godot} — туда его ставит stairwell.tscn (узел YurchikRoom)."""
    os.makedirs(ITEM_DIR, exist_ok=True)
    layout = {}
    for item, it in I.items.items():
        sub = bpy.data.collections.new("yr_" + item)
        coll.children.link(sub)
        obs = [b.build(nm, sub) for (b, nm) in it["parts"].values()]
        for ob in obs:
            if ob.name.endswith("-colonly"):            # невидимые в игре ящики-коллизии: в Blender — каркасом
                ob.display_type = 'WIRE'
        for ob in it["extra"]:
            for c in list(ob.users_collection):
                c.objects.unlink(ob)
            sub.objects.link(ob)
        pts = [v.co for ob in obs for v in ob.data.vertices] + \
              [ob.location + v.co for ob in it["extra"] for v in ob.data.vertices]
        lo = [min(p[i] for p in pts) for i in range(3)]
        hi = [max(p[i] for p in pts) for i in range(3)]
        A = Vector((round((lo[0] + hi[0]) / 2, 3), round((lo[1] + hi[1]) / 2, 3),
                    round(hi[2] if item in ANCHOR_TOP else lo[2], 3)))
        for ob in obs:
            ob.data.transform(Matrix.Translation(-A))
        for ob in it["extra"]:
            ob.location -= A
        allobs = obs + it["extra"]
        export(os.path.join("yurchik_room", item), allobs)
        for ob in obs:                       # в Blender предмет остаётся на своём месте, начало координат — у основания
            ob.location = A
        for ob in it["extra"]:
            ob.parent = obs[0]
        layout[item] = [round(A.x, 3), round(A.z, 3), round(-A.y, 3)]      # Blender Z-up → Godot Y-up
    with open(os.path.join(ITEM_DIR, "layout.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(layout, f, ensure_ascii=False, indent=1)
    return layout


def export(name, obs):
    for o in bpy.context.scene.objects:
        o.select_set(o in obs)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + ".gltf"), use_selection=True, export_keep_originals=True,
                              export_format='GLTF_SEPARATE', export_apply=True, export_yup=True)


# =====================================================================================
#  Комната
# =====================================================================================
def room(M):
    import random
    rng = random.Random(47)
    coll = bpy.context.scene.collection
    I = Items()
    srng = np.random.default_rng(306)
    at = M["atlas"]
    BL, WH = RC("black"), RC("white")
    shell = I("room_shell", "solid")

    # --- пол, потолок ---
    shell.box((X0, Y0, Z - 0.1), (XF, Y1, Z), {'+Z': M["floor"]}, scale=(2.0, 2.0))
    shell.box((X0, Y0, ZT), (XF, Y1, ZT + 0.1), {'-Z': M["ceiling"]}, scale=(1.6, 1.6))

    # --- северная стена: фактурные панели ---
    shell.box((X0, Y1, Z), (X1, Y1 + 0.2, ZT), {'-Y': (M["panels"], (0, 0, 1, 1))})   # одна текстура на всю стену
    # --- южная стена: одна текстура на всю стену (левый край = у двери) ---
    shell.box((X0, Y0 - 0.2, Z), (X1, Y0, ZT), {'+Y': (M["south"], (0, 0, 1, 1))})
    # --- восточная стена с проёмом в коридор ---
    ue = lambda y: (Y1 - y) / (Y1 - Y0)
    vz = lambda z: (z - Z) / H
    for (ya, yb, za, zb) in ((Y0, DOOR_Y0, Z, ZT), (DOOR_Y1, Y1, Z, ZT), (DOOR_Y0, DOOR_Y1, Z + DOOR_H, ZT)):
        shell.box((X1, ya, za), (X1 + 0.12, yb, zb), {'-X': (M["east"], (ue(yb), vz(za), ue(ya), vz(zb)))})
    # --- западная стена с окном (ниша глубиной 22 см) ---
    WY0, WY1, WZ0, WZ1 = 1.76, 3.13, Z + 0.9, Z + 2.34      # как на фото: 1.37 x 1.44 м, подоконник на 0.9 м
    XW = X0 - 0.22
    WS = (2.5, 2.5)
    for (ya, yb, za, zb) in ((Y0, WY0, Z, ZT), (WY1, Y1, Z, ZT), (WY0, WY1, Z, WZ0), (WY0, WY1, WZ1, ZT)):
        shell.box((X0 - 0.2, ya, za), (X0, yb, zb), {'+X': M["west"]}, scale=WS)
    # Откосы, рама со стёклами и подоконник — отдельная 3D-модель (tools/blender/build_room_window.py →
    # room_window.gltf), стоит в stairwell.tscn в точке (X0, WY0, WZ0). Текстура yr_window больше не нужна
    # (tex_window только тратит случайности, чтобы не сдвинуть остальные текстуры).
    # батарея и стояк
    # чугунная батарея МС-140 под левой половиной окна (как на фото): 8 секций — по две круглые колонки с перемычкой,
    # сверху и снизу секции соединены ниппелями (сквозные трубы). Коллизия — простой ящик (см. col ниже)
    rad = I("radiator")
    NS_, RY0, RY1 = 8, 2.08, 2.80
    sw = (RY1 - RY0) / NS_
    for k in range(NS_):
        yc = RY0 + sw * (k + 0.5)
        for xc in (X0 + 0.065, X0 + 0.115):
            cylr(rad, (xc, yc, Z + 0.15), (xc, yc, Z + 0.75), 0.021, 0.021, at, WH, segs=8)
        abox(rad, (X0 + 0.065, yc - 0.006, Z + 0.20), (X0 + 0.115, yc + 0.006, Z + 0.70), at, WH)
    for zc in (Z + 0.19, Z + 0.71):
        cylr(rad, (X0 + 0.09, RY0 + 0.004, zc), (X0 + 0.09, RY1 - 0.004, zc), 0.03, 0.03, at, WH, segs=8)
    for z in (Z + 0.22, Z + 0.68):
        cylr(rad, (X0 + 0.06, 1.5, z), (X0 + 0.06, 2.08, z), 0.016, 0.016, M["radiator_m"], (0, 0, 1, 1), segs=6, caps=False)
    cylr(rad, (X0 + 0.06, 1.5, Z), (X0 + 0.06, 1.5, ZT), 0.022, 0.022, M["radiator_m"], (0, 0, 1, 1), segs=6, caps=False)

    # --- дверь: наличник (часть стены); само полотно — отдельная модель room_door.gltf (build_room_door.py) ---
    for (mn, mx) in (((X1 - 0.02, DOOR_Y0 - 0.08, Z), (X1, DOOR_Y0, Z + DOOR_H + 0.08)),
                     ((X1 - 0.02, DOOR_Y1, Z), (X1, DOOR_Y1 + 0.08, Z + DOOR_H + 0.08)),
                     ((X1 - 0.02, DOOR_Y0, Z + DOOR_H), (X1, DOOR_Y1, Z + DOOR_H + 0.08))):
        abox(I("room_shell"), mn, mx, at, WH)

    # --- люстра: три плафона (игра ищет Chandelier_nocol — гасит и зажигает плафоны) ---
    lamp = I("chandelier")
    cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
    # цилиндры строим снизу вверх: иначе грани смотрят внутрь
    cylr(lamp, (cx, cy, ZT - 0.2), (cx, cy, ZT), 0.008, 0.008, at, RC("brass"), segs=4)
    cylr(lamp, (cx, cy, ZT - 0.26), (cx, cy, ZT - 0.19), 0.02, 0.05, at, RC("brass"), segs=6)
    for k in range(3):
        a = math.radians(90 + k * 120)
        ex, ey = cx + math.cos(a) * 0.22, cy + math.sin(a) * 0.22
        cylr(lamp, (cx, cy, ZT - 0.22), (ex, ey, ZT - 0.18), 0.008, 0.008, at, RC("brass"), segs=4, caps=False)
        cylr(lamp, (ex, ey, ZT - 0.30), (ex, ey, ZT - 0.17), 0.03, 0.085, M["glass"], (0, 0, 1, 1), segs=8)   # плафон-тюльпан

    # --- комод под скатертью (как на фото): в углу у окна, от южной стены до левого края окна,
    #     4 ящика (нижний выдвинут), белая скатерть свисает спереди почти до пола, слева видны ящики ---
    cx0, cx1, cy0, cy1, ch = X0 + 0.07, X0 + 0.52, Y0 + 0.03, Y0 + 0.88, Z + 0.82          # отступ — за ним стояк
    abox(I("dresser", "solid"), (cx0, cy0, Z), (cx1, cy1, ch), at, RC("wood"), faces={'+X': (at, RC("drawer"))})
    dr_ = RC("drawer")
    abox(I("dresser"), (cx1, cy0 + 0.03, Z + 0.03), (cx1 + 0.06, cy1 - 0.03, Z + 0.19), at, RC("wood"),        # нижний ящик выдвинут
         faces={'+X': (at, (dr_[0], dr_[1], dr_[2], dr_[1] + (dr_[3] - dr_[1]) * 0.24))})
    # белая скатерть: на крышке, спереди свисает до выдвинутого нижнего ящика (у южной стены — коротко, там видны ящики), сбоку — до середины
    fhang = lambda y: 0.04 if y < cy0 + 0.22 else (ch - Z - 0.22) * min(1.0, (y - cy0 - 0.22) / 0.06)
    drape(I("tablecloth", "soft"), cx0 - 0.01, cx1 + 0.065, cy0, cy1 + 0.01, ch + 0.006, {'+X': fhang, '+Y': 0.52, '-Y': 0.02, '-X': 0.0},
          at, RC("cloth"), srng, n=(5, 8), nh=5, amp=0.004, edge=0.012, fold=0.012)
    t = ch + 0.012
    plant(I("spathiphyllum"), (cx0 + 0.15, cy0 + 0.16, t), 13, 0.40, M, rng, spread=60)                  # большой спатифиллум
    obox(I("icon_frame"), (cx0 + 0.34, cy0 + 0.17, t + 0.02), (0.20, 0.26, 0.035), at, RC("wood"),      # рамка лежит на краю
         faces={'+Z': (at, RC("picture"))}, yaw=4)
    abox(I("black_boxes"), (cx0 + 0.10, cy0 + 0.32, t), (cx0 + 0.26, cy0 + 0.46, t + 0.11), at, BL)     # чёрные коробочки
    abox(I("black_boxes"), (cx0 + 0.28, cy0 + 0.36, t), (cx0 + 0.40, cy0 + 0.48, t + 0.06), at, BL)
    books = I("book_stack")                                                                          # стопка книг
    obox(books, (cx0 + 0.18, cy0 + 0.58, t + 0.03), (0.18, 0.24, 0.06), at, RC("book"), yaw=12)
    obox(books, (cx0 + 0.18, cy0 + 0.57, t + 0.075), (0.16, 0.22, 0.04), at, RC("book"), yaw=-8)
    obox(books, (cx0 + 0.19, cy0 + 0.58, t + 0.11), (0.15, 0.20, 0.03), at, RC("book"), yaw=20)
    abox(I("charger"), (cx0 + 0.08, cy0 + 0.70, t), (cx0 + 0.18, cy0 + 0.80, t + 0.07), at, WH)          # зарядка/роутер
    obox(I("dresser_phone"), (cx0 + 0.34, cy0 + 0.62, t + 0.005), (0.07, 0.14, 0.01), at, BL, yaw=20)   # телефон
    for k_ in range(4):                                                                              # провода от зарядки
        cylr(I("charger"), (cx0 + 0.13, cy0 + 0.70, t + 0.01), (cx0 + 0.25 + k_ * 0.04, cy0 + 0.40 + k_ * 0.06, t + 0.004),
             0.004, 0.004, at, BL, segs=3, caps=False)

    # --- подоконник: цветок в оранжевом горшке, бутылка, ручка ---
    plant(I("sill_plant"), (X0 + 0.06, 1.95, WZ0), 7, 0.28, M, rng, spread=45)
    sb_ = I("sill_bottle")
    cylr(sb_, (X0 + 0.08, 2.14, WZ0), (X0 + 0.08, 2.14, WZ0 + 0.26), 0.04, 0.04, at, RC("bottle"), segs=8)
    cylr(sb_, (X0 + 0.08, 2.14, WZ0 + 0.26), (X0 + 0.08, 2.14, WZ0 + 0.31), 0.04, 0.014, at, RC("bottle"), segs=8, caps=False)
    cylr(sb_, (X0 + 0.08, 2.14, WZ0 + 0.31), (X0 + 0.08, 2.14, WZ0 + 0.33), 0.015, 0.015, at, RC("cap"), segs=6)
    obox(I("sill_pen"), (X0 + 0.15, 2.75, WZ0 + 0.005), (0.012, 0.14, 0.01), at, RC("cap"), yaw=-25)

    # --- кресло с одеждой (как на фото): во весь угол — от стены с окном до подлокотника дивана,
    #     спинкой к стене с панелями; округлая спинка, вся обивка — тёмная ткань в цветах (как плед на спинке), гора одежды сползает к батарее ---
    fab = M["fabric"]
    af = M["armchair"]
    FS = lambda w_, h_: (0, 0, w_ / 0.5, h_ / 0.5)              # велюр: тайл 0.5 м
    sx0_ = X0 + 1.2                                             # где начинается диван (см. ниже)
    ax0, ax1, ay0, ay1 = X0 + 0.02, sx0_ - 0.05, Y1 - 0.86, Y1 - 0.04
    AW = ax1 - ax0
    axc = (ax0 + ax1) / 2
    chair = I("armchair", "soft")
    soft(chair, (axc, (ay0 + ay1 - 0.2) / 2, Z + 0.22), (AW - 0.30, ay1 - 0.2 - ay0, 0.44), af, FS(AW, 0.6), r=0.07, n=(3, 3, 2), sag=0.03)
    soft(chair, (axc, ay1 - 0.13, Z + 0.46), (AW, 0.26, 0.92), af, FS(AW, 1.0), r=0.12, n=(4, 1, 3), taper=0.97)        # спинка, округлый верх
    for xc in (ax0 + 0.08, ax1 - 0.08):                                                                         # толстые подлокотники
        soft(chair, (xc, (ay0 + 0.04 + ay1 - 0.2) / 2, Z + 0.30), (0.17, ay1 - 0.24 - ay0, 0.62), af, FS(0.2, 0.6), r=0.08, n=(1, 3, 2))
    # на спинку наброшен серо-сиреневый плед с блёклыми цветами (как на фото)
    drape(I("armchair_throw", "soft"), ax0 + 0.02, ax1 - 0.02, ay1 - 0.24, ay1 - 0.02, Z + 0.925, {'-Y': 0.30, '+Y': 0.05, '-X': 0.12, '+X': 0.10},
          af, (0, 0, 2.2, 1.2), srng, n=(6, 2), nh=3, amp=0.01, edge=0.06, fold=0.025)
    cl = CLQ(1)
    pile_i = [0]
    pile = I("clothes_pile", "soft")
    # гора одежды (мягкие комья): выше подлокотников, ниже спинки; часть сползает к батарее и на пол
    for (dx, fy, dz, sx, sy, sz, yw, pt) in (
            (0.50, 0.45, 0.50, 0.55, 0.66, 0.20, 8, 0), (0.46, 0.58, 0.66, 0.44, 0.50, 0.18, -14, 4),
            (0.54, 0.32, 0.74, 0.32, 0.38, 0.14, 25, 6), (0.60, 0.76, 0.60, 0.32, 0.32, 0.22, 40, 0),
            (0.58, 0.18, 0.62, 0.30, 0.28, 0.22, 10, 0), (0.40, 0.66, 0.80, 0.28, 0.32, 0.14, -30, 0),
            (0.72, 0.45, 0.40, 0.52, 0.42, 0.30, -6, -25),
            (0.68, 0.10, 0.36, 0.40, 0.24, 0.44, 15, -18)):
        q_ = (0, 1, 0, 2, 3, 1, 0, 3)[pile_i[0] % 8]; pile_i[0] += 1
        soft(pile, (ax0 + fy * AW, ay1 - dx, Z + dz), (sy, sx, sz), at, CLQ(q_), r=min(sx, sy, sz) * 0.35, n=(2, 2, 1),
             amp=0.028, rng=srng, yaw=yw, pitch=pt, freq=14)
    soft(SB(), (ax0 + 0.16, ay0 - 0.05, Z + 0.30), (0.30, 0.06, 0.56), at, cl, r=0.025, n=(2, 1, 3), amp=0.01, rng=srng, yaw=8, pitch=-14)   # джинсы убраны; вызов оставлен в пустую сетку, чтобы не сдвинуть случайные числа у пледа и одежды на полу
    soft(pile, (ax0 + 0.62 * AW, ay0 - 0.03, Z + 0.32), (0.12, 0.03, 0.44), at, WH, r=0.012, n=(1, 1, 3), amp=0.006, rng=srng, yaw=-4, pitch=-8)  # белое полотенце
    soft(I("armchair_box", "soft"), (ax0 + 0.55 * AW, ay0 - 0.30, Z + 0.20), (0.50, 0.08, 0.40), at, BL, r=0.01, n=(1, 1, 1), yaw=-8, pitch=-28)   # чёрная коробка у кресла
    soft(I("floor_clothes", "soft"), (ax0 + 0.22, ay0 - 0.22, Z + 0.06), (0.38, 0.30, 0.13), at, cl, r=0.06, n=(2, 2, 1), amp=0.015, rng=srng, yaw=20, freq=12)   # куча на полу
    for k_ in range(2):                                                                            # провода из-под коробки
        cylr(I("armchair_box"), (ax0 + 0.5 * AW + k_ * 0.08, ay0 - 0.36, Z + 0.01), (ax0 + 0.5 * AW + 0.22 + k_ * 0.05, ay0 - 0.70, Z + 0.01), 0.005, 0.005, at, BL, segs=3, caps=False)
    for (y_, yw) in ((2.78, 75), (2.56, 95)):                                                      # кроссовки у батареи
        soft(I("sneakers", "soft"), (X0 + 0.30, y_, Z + 0.06), (0.10, 0.27, 0.09), at, WH, r=0.04, n=(1, 2, 1), yaw=yw, taper=0.8)
        soft(I("sneakers", "soft"), (X0 + 0.30, y_, Z + 0.013), (0.115, 0.29, 0.026), at, BL, r=0.012, n=(1, 2, 1), yaw=yw)

    # --- диван-кровать вдоль северной стены, разложен ---
    sx0, sx1 = X0 + 1.2, -7.58                                                 # вплотную к креслу; между комодом и кроватью — проход к окну
    sy1 = Y1 - 0.02
    SW = sx1 - sx0
    bl = M["blanket"]
    sofa = I("sofa", "soft")
    soft(sofa, ((sx0 + sx1) / 2, (2.0 + sy1) / 2, Z + 0.16), (SW, sy1 - 2.0, 0.32), fab, FS(SW, 1.9), r=0.04, n=(4, 3, 1))
    soft(sofa, ((sx0 + sx1) / 2, sy1 - 0.13, Z + 0.59), (SW, 0.26, 0.56), fab, FS(SW, 0.6), r=0.09, n=(5, 1, 2), sag=0.02)  # спинка
    for xc in (sx0 + 0.08, sx1 - 0.08):                                                         # подлокотники: толстые, скруглённые
        soft(sofa, (xc, sy1 - 0.475, Z + 0.34), (0.26, 0.95, 0.68), fab, FS(0.3, 1.0), r=0.11, n=(1, 3, 2))
    # разложенная часть выдвинута далеко от стены (как на фото): шириной с диван; до стены с мангой проход ~0.7 м
    by0, by1 = Y0 + 0.70, sy1 - 0.95                                           # by1 — перед подлокотниками
    soft(sofa, ((sx0 + sx1) / 2, (by0 + 0.10 + sy1 - 0.26) / 2, Z + 0.20), (SW, sy1 - 0.26 - by0 - 0.10, 0.40), fab,
         FS(SW, 2.2), r=0.05, n=(4, 5, 1))
    # плед наброшен на кровать и свисает спереди и по бокам; ком посередине, складки
    side = lambda y: 0.28 if y < by1 - 0.05 else 0.0
    drape(I("sofa_blanket", "soft"), sx0 - 0.02, sx1 + 0.02, by0 + 0.08, sy1 - 0.28, Z + 0.44, {'-Y': 0.32, '-X': side, '+X': side, '+Y': 0.02},
          bl, (0, 0, 1, 1), srng, n=(12, 16), nh=4, amp=0.018, edge=0.05, fold=0.03,
          bumps=[(sx0 + 0.75, by0 + 0.80, 0.30, 0.12), (sx0 + 1.1, by0 + 1.35, 0.25, 0.07), (sx0 + 0.4, by0 + 0.4, 0.2, 0.05)])
    soft(I("pillow", "soft"), (sx0 + 0.55, sy1 - 0.45, Z + 0.53), (0.38, 0.34, 0.12), at, RC("pillow"), r=0.06, n=(2, 2, 1), sag=-0.02, yaw=10)   # подушка

    # --- компьютерный стол в северо-восточном углу ---
    dx0, dx1, dy0, dy1 = -7.48, X1 - 0.02, Y1 - 0.64, Y1 - 0.02
    dt = Z + 0.74
    desk = I("desk", "solid")
    abox(desk, (dx0, dy0, dt - 0.03), (dx1, dy1, dt), at, BL)
    for (x, y) in ((dx0 + 0.03, dy0 + 0.03), (dx1 - 0.03, dy0 + 0.03), (dx0 + 0.03, dy1 - 0.03), (dx1 - 0.03, dy1 - 0.03)):
        abox(desk, (x - 0.025, y - 0.025, Z), (x + 0.025, y + 0.025, dt - 0.03), at, BL)
    abox(desk, (dx0 + 0.03, dy1 - 0.05, Z + 0.12), (dx1 - 0.03, dy1 - 0.03, Z + 0.5), at, BL)     # задняя стенка
    abox(I("mousepad"), (dx0 + 0.04, dy0 + 0.02, dt), (dx0 + 0.82, dy0 + 0.34, dt + 0.003), at, RC("mousepad"))
    mx = -7.02
    # монитор 19" 5:4 на подставке; экран — отдельный объект PCScreen_nocol (игра его «включает»)
    mon = I("monitor")
    abox(mon, (mx - 0.12, dy1 - 0.30, dt), (mx + 0.12, dy1 - 0.12, dt + 0.015), at, BL)
    abox(mon, (mx - 0.03, dy1 - 0.20, dt + 0.015), (mx + 0.03, dy1 - 0.16, dt + 0.17), at, BL)
    abox(I("monitor", "solid"), (mx - 0.215, dy1 - 0.23, dt + 0.11), (mx + 0.215, dy1 - 0.17, dt + 0.47), at, BL)
    abox(mon, (mx - 0.12, dy1 - 0.17, dt + 0.17), (mx + 0.12, dy1 - 0.10, dt + 0.40), at, BL)
    I("monitor", "detail", name="PCScreen_nocol").box((mx - 0.19, dy1 - 0.232, dt + 0.135), (mx + 0.19, dy1 - 0.231, dt + 0.445),
                                                      {'-Y': (M["screen"], (0, 0, 1, 1))})
    # системный блок на столе, справа от монитора
    abox(I("pc_tower", "solid"), (dx1 - 0.215, dy0 + 0.08, dt), (dx1 - 0.025, dy0 + 0.55, dt + 0.43), at, RC("tower_s"),
         faces={'-Y': (at, RC("tower_f")), '+Z': (at, BL), '+Y': (at, BL)})
    # колонки 2.0
    for x, nm in ((mx - 0.40, "speaker_left"), (dx1 - 0.33, "speaker_right")):
        abox(I(nm), (x - 0.05, dy1 - 0.22, dt), (x + 0.05, dy1 - 0.13, dt + 0.18), at, BL, faces={'-Y': (at, RC("speaker"))})
    # клавиатура, мышь, кружка, бутылки
    abox(I("keyboard"), (mx - 0.23, dy0 + 0.06, dt + 0.003), (mx + 0.23, dy0 + 0.22, dt + 0.025), at, BL, faces={'+Z': (at, RC("keyb"))})
    obox(I("mouse"), (mx + 0.33, dy0 + 0.14, dt + 0.018), (0.062, 0.11, 0.03), at, BL, yaw=-8)
    cylr(I("mouse"), (mx + 0.33, dy0 + 0.19, dt + 0.03), (mx + 0.25, dy0 + 0.40, dt + 0.003), 0.003, 0.003, at, BL, segs=3, caps=False)
    cylr(I("mug"), (dx0 + 0.12, dy0 + 0.26, dt), (dx0 + 0.12, dy0 + 0.26, dt + 0.10), 0.042, 0.042, at, RC("mug"), segs=8)
    for (x, y, hh, nm) in ((dx0 + 0.13, dy1 - 0.14, 0.30, "desk_bottle_tall"), (dx0 + 0.26, dy1 - 0.10, 0.24, "desk_bottle_short")):
        cylr(I(nm), (x, y, dt), (x, y, dt + hh), 0.045, 0.045, at, RC("bottle"), segs=8)
        cylr(I(nm), (x, y, dt + hh), (x, y, dt + hh + 0.06), 0.045, 0.015, at, RC("bottle"), segs=8, caps=False)
        cylr(I(nm), (x, y, dt + hh + 0.06), (x, y, dt + hh + 0.08), 0.016, 0.016, at, RC("cap"), segs=6)
    # миска с ложкой и красная мягкая игрушка на системнике (как на фото стены)
    bx_, by_ = dx0 + 0.17, dy0 + 0.09
    bowl = I("bowl")
    cylr(bowl, (bx_, by_, dt), (bx_, by_, dt + 0.055), 0.035, 0.07, at, WH, segs=8)
    cylr(bowl, (bx_, by_, dt + 0.05), (bx_, by_, dt + 0.052), 0.058, 0.058, at, RC("soil"), segs=8)
    obox(bowl, (bx_ + 0.05, by_ + 0.04, dt + 0.07), (0.012, 0.17, 0.005), at, WH, yaw=-55, pitch=18)
    cylr(I("plush_toy"), (dx1 - 0.12, dy0 + 0.33, dt + 0.43), (dx1 - 0.12, dy0 + 0.33, dt + 0.54), 0.07, 0.06, at, RC("plush"), segs=8)
    # провода из-под стола: вниз за столом, по полу вдоль стены к розетке под выключателем
    for k in range(3):
        y_, zz = 2.24 - k * 0.012, Z + 0.33 + k * 0.012
        pts_ = [(dx1 - 0.1 - k * 0.05, dy1 - 0.08, dt), (X1 - 0.03 - k * 0.01, Y1 - 0.3, Z + 0.015),
                (X1 - 0.03 - k * 0.01, y_ + 0.06, Z + 0.015), (X1 - 0.015, y_, zz)]
        for a_, b_ in zip(pts_, pts_[1:]):
            cylr(I("desk_cables"), a_, b_, 0.004, 0.004, at, BL, segs=3, caps=False)

    # надписи маркером — прозрачная наклейка в 4 мм от стены
    I("wall_writing", "detail", name="EastWriting_nocol").box((X1 - 0.005, WR_Y0, Z + WR_Z0), (X1 - 0.004, WR_Y1, Z + WR_Z1),
                                                             {'-X': (M["writing"], (0, 0, 1, 1))})

    # игровое кресло — отдельная модель gaming_chair.gltf (build_gaming_chair.py), стоит в stairwell.tscn у стола

    # --- коллизии мягкой мебели: простые ящики (сетка обивки слишком подробная для физики) ---
    CF = {k: at for k in ('+X', '-X', '+Y', '-Y', '+Z', '-Z')}
    I("radiator", "col").box((X0 + 0.04, 2.08, Z + 0.15), (X0 + 0.14, 2.80, Z + 0.75), CF)               # батарея
    I("armchair", "col").box((ax0, ay0 - 0.05, Z), (ax1, ay1, Z + 0.92), CF)                               # кресло с одеждой
    obox(I("armchair_box", "col"), (ax0 + 0.55 * AW, ay0 - 0.30, Z + 0.20), (0.50, 0.08, 0.40), at, BL, yaw=-8, pitch=-28)   # коробка у кресла
    sc = I("sofa", "col")
    sc.box((sx0, 2.0, Z), (sx1, sy1, Z + 0.32), CF)                                                        # диван: основание
    sc.box((sx0, sy1 - 0.26, Z), (sx1, sy1, Z + 0.87), CF)                                                 # спинка
    for (xa, xb) in ((sx0 - 0.05, sx0 + 0.21), (sx1 - 0.21, sx1 + 0.05)):                                  # подлокотники
        sc.box((xa, sy1 - 0.95, Z), (xb, sy1, Z + 0.68), CF)
    sc.box((sx0, by0 + 0.10, Z), (sx1, sy1 - 0.26, Z + 0.44), CF)                                          # кровать с пледом

    # --- выключатель света у проёма (поверх нарисованного на стене): рамка и отдельная клавиша —
    #     игра качает клавишу (stairwell.gd: _toggle_light), ось — у поверхности рамки ---
    SWY, SWZ = 2.10, Z + 1.55
    abox(I("light_switch"), (X1 - 0.012, SWY - 0.04, SWZ - 0.078), (X1, SWY + 0.04, SWZ + 0.078), at, WH, skip=('+X',))
    kb = B()
    abox(kb, (-0.014, -0.025, -0.045), (0.0, 0.025, 0.045), at, WH, skip=('+X',))
    abox(kb, (-0.0145, -0.012, 0.028), (-0.0135, 0.012, 0.032), at, BL, faces=None, skip=('+X',))   # риска сверху
    key = kb.build("LightSwitchKey_nocol", coll)
    key.location = (X1 - 0.012, SWY, SWZ)
    I.extra("light_switch", key)

    layout = export_items(I, coll)
    return {"items": len(layout), "layout": layout}


def mat_alpha(name, tex):
    """Материал-наклейка: цвет и прозрачность из PNG (экспорт в glTF как alphaMode BLEND)."""
    m = mat(name, tex, rough=0.8)
    nt = m.node_tree
    t = next(n for n in nt.nodes if n.type == 'TEX_IMAGE')
    nt.links.new(t.outputs["Alpha"], nt.nodes["Principled BSDF"].inputs["Alpha"])
    m.surface_render_method = 'BLENDED'
    return m


def main():
    for ob in list(bpy.context.scene.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for c in list(bpy.context.scene.collection.children):     # коллекции предметов с прошлой сборки
        if c.name.startswith("yr_"):
            bpy.data.collections.remove(c)
    tex_panels(); tex_west(); tex_south(); tex_east(); tex_floor_ceiling()
    tex_blanket(); tex_fabric(); tex_window(); tex_screen(); tex_atlas()
    render_writing()
    M = {
        "panels": mat("YrPanels", "yr_panels"), "west": mat("YrWest", "yr_west"), "south": mat("YrSouth", "yr_south"),
        "east": mat("YrEast", "yr_east"), "floor": mat("YrLaminate", "yr_laminate", rough=0.5),
        "ceiling": mat("YrCeiling", "yr_ceiling"), "blanket": mat("YrBlanket", "yr_blanket"),
        "fabric": mat("YrFabric", "yr_fabric"), "armchair": mat("YrArmchair", "yr_armchair"),
        "screen": mat("YrScreen", "yr_screen", "yr_screen_emission", rough=0.2), "atlas": mat("YrAtlas", "yr_atlas", rough=0.7),
        "radiator": mat("YrRadiator", "radiator", rough=0.6), "radiator_m": mat("YrPipe", "radiator", rough=0.6),
        "glass": mat("YrLampGlass", "lamp_glass", "lamp_glass", rough=0.3),
        "writing": mat_alpha("YrWriting", "yr_writing"),
    }
    res = room(M)
    print("BUILD_YUR_ROOM " + json.dumps(res))
    return res


main()
