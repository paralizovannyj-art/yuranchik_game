# -*- coding: utf-8 -*-
# Комната Юрчика в квартире 47 (задача YUR-17) — по фотографиям настоящей комнаты.
#
# Что в комнате (как на фото):
#   * окно в белой пластиковой раме, под ним батарея, на подоконнике цветок в оранжевом горшке и бутылка воды;
#   * слева от окна — комод под белой скатертью: спатифиллум, икона в рамке, коробки, книги;
#   * справа от окна — кресло, заваленное одеждой;
#   * вдоль длинной стены — разложенный диван с подлокотниками и цветастым пледом (розы, медальон, «леопардовая» кайма);
#     стена над диваном — бежевые фактурные панели с рядом дырок от дюбелей;
#   * в углу у двери — чёрный компьютерный стол и зелёно-чёрное игровое кресло;
#   * компьютер образца 2010–2011: квадратный LCD-монитор 19" (5:4), чёрный корпус с DVD-приводом стоит НА столе,
#     колонки 2.0, клавиатура, мышь. Никакого маленького RGB-компа под столом;
#   * белая стена с дверью: над столом надписи красным маркером (как на фото — текст в списке WRITING),
#     над ними гирлянда с зелёными бусинами; выключатель на 1.5 м у проёма, розетка под ним;
#     на столе миска с ложкой, на системнике красная мягкая игрушка;
#   * стена напротив дивана — у двери коллаж из страниц манги почти до потолка (страницы свои, процедурные);
#     люстра с тремя плафонами, светлый ламинат.
#
# Запуск (Blender 5.2, из корня проекта; надписи рисуются шрифтами Windows Segoe Print и Ink Free):
#   blender -b --factory-startup --python tools/blender/build_yurchik_room.py
# Результат: assets/textures/yr_*.png (yr_writing.png — с прозрачностью), assets/models/yurchik_room.gltf
#
# Координаты — те же, что у подъезда (build_mvp_assets.py): комната на 4-м этаже, x −10.5…−6.32, y 0.95…3.9,
# пол на z = 8.4. Поэтому модель ставится в stairwell.tscn без смещения.
# Объекты: YurRoom — стены и мебель (с коллизией), YurRoomProps_nocol — мелочь, PCScreen_nocol — экран монитора
# (отдельно, чтобы игра могла его «включить»), EastWriting_nocol — прозрачная наклейка с надписями.
import bpy, os, sys, math
import numpy as np
from mathutils import Vector, Euler

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
def tex_panels():
    """Бежевые фактурные панели над диваном: «штукатурка-шуба» с разводами шпателя, стыки, дырки от дюбелей."""
    w = h = 256
    n = noise(w, h, 8, 8, R, oct=5)
    n2 = noise(w, h, 24, 24, R, oct=3)
    hgt = n * 0.7 + n2 * 0.3
    sh = 1 + ((hgt - np.roll(hgt, 1, 1)) + (hgt - np.roll(hgt, 1, 0))) * 6        # рельеф, свет сверху-слева
    swirl = 0.95 + 0.05 * np.sin(hgt * 46)                                         # мазки шпателя
    arr = np.ones((h, w, 3), np.float32) * C(0.70, 0.65, 0.53)
    arr *= (sh * swirl)[..., None]
    arr *= mottle(h, w, R, 2, 0.12)[..., None]
    for k in (0, 128):                                                             # стыки панелей 1.2 x 1.2 м
        arr[k:k + 1] *= 0.55; arr[k + 1:k + 2] *= 1.08
        arr[:, k:k + 1] *= 0.6; arr[:, k + 1:k + 2] *= 1.06
    for py in (52, 180):                                                           # ряд дырок от дюбелей
        for px in range(10, 256, 21):
            x = px + int(R.integers(-3, 4)); y = py + int(R.integers(-2, 3))
            arr[y:y + 3, x:x + 3] = C(0.10, 0.08, 0.06)
            arr[y + 3:y + 4, x:x + 3] *= 0.8
    save("yr_panels", finish(arr, 1.2))


def tex_west():
    """Стена с окном: пожелтевшая побелка в разводах."""
    arr = plaster(R, 256, 256, (0.70, 0.66, 0.53), streak=0.3, stains=0.45, crack=0.3)
    arr = peeled(arr, R, C(0.52, 0.50, 0.44), 12, 0.05)
    save("yr_west", finish(arr, 1.25))


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
    """Стена напротив дивана: побелка; у двери (левый край текстуры) — коллаж из страниц манги почти до потолка,
    ряды к низу обрываются неровно, как на фото. 1024 x 512 на 3.88 x 2.5 м."""
    w, h = 1024, 512
    arr = plaster(R, w, h, (0.76, 0.75, 0.70), streak=0.2, stains=0.3, crack=0.25)
    arr = peeled(arr, R, C(0.56, 0.54, 0.48), 16, 0.04)
    arr *= (1 - floor_grime(h, w, R, 0.25, 0.45))[..., None]
    ppm_x, ppm_y = w / (X1 - X0), h / H                        # пикселей на метр
    PW, PH = 0.205, 0.285                                      # страница, м
    cols_in_row = [range(12)] * 6 + [range(2, 10), [4, 5, 6, 11]]
    top = 2.56                                                 # верх коллажа от пола, м (почти до потолка)
    for r, cols in enumerate(cols_in_row):
        for c in cols:
            x_m = 0.9 + c * PW + RM.uniform(-0.012, 0.012)         # первые 0.9 м у двери — под открытой дверью
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
    arr = plaster(R, w, h, (0.78, 0.77, 0.72), streak=0.2, stains=0.3, crack=0.3)
    top = np.zeros((h, w), np.float32); top[:70] = 1
    top = blur(top[..., None], 8)[..., 0]
    patches = smoothstep(0.55, 0.62, noise(w, h, 10, 5, R, oct=3)) * top
    under = C(0.55, 0.53, 0.47) * (0.85 + 0.3 * noise(w, h, 16, 8, R))[..., None]
    arr = arr * (1 - patches[..., None]) + under * patches[..., None]
    rim = np.clip(patches - np.roll(patches, (2, 2), (0, 1)), 0, 1)
    arr *= (1 - rim * 0.5)[..., None]
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
WR_Y0, WR_Y1, WR_Z0, WR_Z1 = 2.46, 3.86, 0.88, 2.06          # где висит наклейка: y (с севера к двери), высота от пола
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
    save("yr_laminate", ps2_hero.wood_floor(R, 256, 256, 8, base=(0.50, 0.35, 0.21)))   # светлый ламинат «дуб»
    save("yr_ceiling", ps2_hero.ceiling(R, 128))


def tex_blanket():
    """Плед на диване: ржаво-оранжевый, розы, кремовый медальон в центре, «леопардовая» кайма."""
    s = 256
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    u = (xx - s / 2 + 0.5) / (s / 2); v = (yy - s / 2 + 0.5) / (s / 2)
    sq = np.maximum(np.abs(u), np.abs(v))
    arr = np.ones((s, s, 3), np.float32) * C(0.56, 0.24, 0.09)
    # кайма «под леопарда»
    spots = smoothstep(0.62, 0.70, noise(s, s, 28, 28, R, oct=2))
    leo = C(0.72, 0.46, 0.18) * (1 - spots[..., None]) + C(0.20, 0.09, 0.03) * spots[..., None]
    arr = np.where((sq > 0.80)[..., None], leo, arr)
    arr = np.where(((sq > 0.75) & (sq < 0.79))[..., None], C(0.80, 0.66, 0.38), arr)
    # розы с листьями по полю
    def rose(cx, cy, r, base, dark):
        dx, dy = xx - cx, yy - cy
        rr = np.sqrt(dx * dx + dy * dy); a = np.arctan2(dy, dx)
        m = rr < r
        petals = 0.5 + 0.5 * np.sin(a * 3 + rr * 0.9)
        col = base * (1 - petals[..., None] * 0.45) + dark * (petals[..., None] * 0.45)
        return m, col
    pts = [(40, 40), (216, 40), (40, 216), (216, 216), (128, 30), (128, 226), (30, 128), (226, 128),
           (72, 90), (184, 90), (72, 166), (184, 166)]
    for (cx, cy) in pts:
        for k in range(3):                                       # листья
            ang = R.random() * 6.28; lx, ly = cx + math.cos(ang) * 11, cy + math.sin(ang) * 11
            lm = ((xx - lx) / 7) ** 2 + ((yy - ly) / 3.5) ** 2 < 1
            arr = np.where(lm[..., None], C(0.30, 0.40, 0.16), arr)
        m, col = rose(cx + R.integers(-4, 5), cy + R.integers(-4, 5), 9 + R.integers(0, 4), C(0.86, 0.56, 0.42), C(0.52, 0.18, 0.12))
        arr = np.where(m[..., None], col, arr)
    # медальон
    e = (u / 0.46) ** 2 + (v / 0.34) ** 2
    arr = np.where((e < 1.0)[..., None], C(0.82, 0.70, 0.46), arr)
    arr = np.where((e < 0.82)[..., None], C(0.70, 0.50, 0.28), arr)
    ring = (e > 0.86) & (e < 0.95)
    arr = np.where(ring[..., None], C(0.48, 0.20, 0.10), arr)
    m, col = rose(128, 128, 22, C(0.90, 0.62, 0.46), C(0.55, 0.20, 0.14))
    arr = np.where(m[..., None], col, arr)
    for (cx, cy) in ((96, 128), (160, 128), (128, 108), (128, 148)):
        m, col = rose(cx, cy, 8, C(0.86, 0.56, 0.42), C(0.52, 0.18, 0.12))
        arr = np.where(m[..., None], col, arr)
    arr *= (0.82 + 0.3 * noise(s, s, 64, 64, R, oct=2))[..., None]        # ворс
    arr *= mottle(s, s, R, 2, 0.12)[..., None]
    save("yr_blanket", finish(blur(arr, 0.6, wrap=False), 1.15, crisp=0.3))


def tex_fabric():
    """Обивка дивана и кресла: серо-бежевый велюр."""
    arr = np.ones((64, 64, 3), np.float32) * C(0.50, 0.44, 0.35)
    arr *= (0.85 + 0.25 * noise(64, 64, 16, 16, R, oct=2) + 0.1 * R.random((64, 64)).astype(np.float32))[..., None]
    arr *= mottle(64, 64, R, 2, 0.15)[..., None]
    save("yr_fabric", finish(arr, 1.1))
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
    """Окно в белой пластиковой раме: две створки, за стеклом ночь, дом напротив с редкими огнями."""
    s = 128
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    g = (yy / s)[..., None]
    glass = C(0.02, 0.03, 0.07) * (1 - g) + C(0.12, 0.08, 0.07) * g
    house = (yy > 34) & (xx > 10) & (xx < 112)
    glass = np.where(house[..., None], C(0.035, 0.035, 0.045), glass)
    lit = np.zeros((s, s), np.float32)
    for wy in range(40, 124, 10):
        for wx in range(16, 108, 9):
            if R.random() < 0.18:
                lit[wy:wy + 5, wx:wx + 4] = 0.6 + 0.4 * R.random()
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
    save("yr_window", finish(alb, 1.1, crisp=0.3))
    save("yr_window_emission", np.where(frame[..., None], 0.0, glass * 0.8 + lit[..., None] * 0.6).astype(np.float32))


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
    "chair_g": (192, 0, 224, 32), "chair_b": (224, 0, 256, 32), "cloth": (192, 32, 256, 64),
    "keyb": (0, 64, 128, 104), "drawer": (0, 104, 64, 168), "wood": (64, 104, 128, 168), "pot": (128, 104, 160, 136),
    "leaf": (160, 104, 192, 136), "picture": (192, 104, 256, 168), "mug": (0, 168, 32, 200), "bottle": (32, 168, 64, 200),
    "book": (64, 168, 128, 200), "clothes": (128, 168, 192, 232), "brass": (224, 168, 256, 200),
    "door": (0, 200, 32, 256), "mousepad": (32, 200, 64, 232), "white": (64, 200, 128, 232), "pillow": (128, 232, 160, 256),
    "soil": (192, 200, 224, 232), "cap": (224, 200, 256, 232),
    "plush": (128, 72, 160, 104), "bead": (160, 72, 192, 104),
}


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
    g = np.ones((32, 32, 3), np.float32) * C(0.09, 0.40, 0.17) * (0.85 + 0.3 * noise(32, 32, 6, 6, R))[..., None]
    g[::8] *= 0.6; put("chair_g", g)
    bk = np.ones((32, 32, 3), np.float32) * C(0.06, 0.06, 0.065) * (0.8 + 0.4 * noise(32, 32, 6, 6, R))[..., None]
    bk[:, ::10] = C(0.10, 0.36, 0.16); put("chair_b", bk)                       # зелёная прострочка
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
    cl = np.ones((64, 64, 3), np.float32) * C(0.20, 0.27, 0.40)
    n1 = noise(64, 64, 5, 5, R, oct=2); n2 = noise(64, 64, 4, 4, R, oct=2)
    cl = np.where((n1 > 0.55)[..., None], C(0.05, 0.05, 0.06), cl)
    cl = np.where((n2 > 0.62)[..., None], C(0.32, 0.33, 0.35), cl)
    cl *= (0.75 + 0.5 * noise(64, 64, 10, 10, R))[..., None]
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
    pl = np.ones((24, 32, 3), np.float32) * C(0.42, 0.36, 0.50) * (0.85 + 0.3 * noise(32, 24, 4, 4, R))[..., None]
    pl[::4, ::4] = C(0.6, 0.55, 0.65); put("pillow", pl)
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
    """Двусторонний лист: от основания под углом tilt от вертикали в сторону yaw (градусы)."""
    y, t = math.radians(yaw), math.radians(tilt)
    base = Vector(base)
    d = Vector((math.cos(y) * math.sin(t), math.sin(y) * math.sin(t), math.cos(t)))
    side = Vector((-math.sin(y), math.cos(y), 0)) * (W / 2)
    mid = base + d * (L * 0.45) - Vector((0, 0, L * 0.05 * math.sin(t)))
    tip = base + d * L - Vector((0, 0, L * 0.25 * math.sin(t)))         # кончик чуть свисает
    u0, v0, u1, v1 = rect
    um, vm = (u0 + u1) / 2, (v0 + v1) / 2
    pts = [base, mid + side, tip, mid - side]
    uvs = [(um, v0), (u1, vm), (um, v1), (u0, vm)]
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
    b, p, scr = B(), B(), B()
    at = M["atlas"]
    BL, WH = RC("black"), RC("white")

    # --- пол, потолок ---
    b.box((X0, Y0, Z - 0.1), (XF, Y1, Z), {'+Z': M["floor"]}, scale=(2.0, 2.0))
    b.box((X0, Y0, ZT), (XF, Y1, ZT + 0.1), {'-Z': M["ceiling"]}, scale=(1.6, 1.6))

    # --- северная стена: фактурные панели ---
    b.box((X0, Y1, Z), (X1, Y1 + 0.2, ZT), {'-Y': M["panels"]}, scale=(2.4, 2.4))
    # --- южная стена: одна текстура на всю стену (левый край = у двери) ---
    b.box((X0, Y0 - 0.2, Z), (X1, Y0, ZT), {'+Y': (M["south"], (0, 0, 1, 1))})
    # --- восточная стена с проёмом в коридор ---
    ue = lambda y: (Y1 - y) / (Y1 - Y0)
    vz = lambda z: (z - Z) / H
    for (ya, yb, za, zb) in ((Y0, DOOR_Y0, Z, ZT), (DOOR_Y1, Y1, Z, ZT), (DOOR_Y0, DOOR_Y1, Z + DOOR_H, ZT)):
        b.box((X1, ya, za), (X1 + 0.12, yb, zb), {'-X': (M["east"], (ue(yb), vz(za), ue(ya), vz(zb)))})
    # --- западная стена с окном (ниша глубиной 22 см) ---
    WY0, WY1, WZ0, WZ1 = 1.76, 3.13, Z + 0.9, Z + 2.34      # как на фото: 1.37 x 1.44 м, подоконник на 0.9 м
    XW = X0 - 0.22
    WS = (2.5, 2.5)
    for (ya, yb, za, zb) in ((Y0, WY0, Z, ZT), (WY1, Y1, Z, ZT), (WY0, WY1, Z, WZ0), (WY0, WY1, WZ1, ZT)):
        b.box((X0 - 0.2, ya, za), (X0, yb, zb), {'+X': M["west"]}, scale=WS)
    b.box((XW, WY0 - 0.01, WZ0), (X0, WY0, WZ1), {'+Y': M["west"]}, scale=WS)
    b.box((XW, WY1, WZ0), (X0, WY1 + 0.01, WZ1), {'-Y': M["west"]}, scale=WS)
    b.box((XW, WY0, WZ1), (X0, WY1, WZ1 + 0.01), {'-Z': M["west"]}, scale=WS)
    b.box((XW - 0.01, WY0, WZ0), (XW, WY1, WZ1), {'+X': (M["window"], (0, 0, 1, 1))})
    abox(b, (XW + 0.04, WY0 - 0.08, WZ0 - 0.04), (X0 + 0.24, WY1 + 0.08, WZ0), at, WH)                 # подоконник
    # батарея и стояк
    b.box((X0 + 0.04, 2.08, Z + 0.15), (X0 + 0.14, 2.8, Z + 0.75),     # батарея под левой половиной окна
          {'+X': (M["radiator"], (0, 0, 1.5, 1)), '+Z': M["radiator"], '+Y': M["radiator"], '-Y': M["radiator"]}, scale=(0.3, 0.3))
    for z in (Z + 0.22, Z + 0.68):
        cylr(p, (X0 + 0.06, 1.5, z), (X0 + 0.06, 2.08, z), 0.016, 0.016, M["radiator_m"], (0, 0, 1, 1), segs=6, caps=False)
    cylr(p, (X0 + 0.06, 1.5, Z), (X0 + 0.06, 1.5, ZT), 0.022, 0.022, M["radiator_m"], (0, 0, 1, 1), segs=6, caps=False)

    # --- дверь: наличник и полотно, открытое в комнату к южной стене ---
    for (mn, mx) in (((X1 - 0.02, DOOR_Y0 - 0.08, Z), (X1, DOOR_Y0, Z + DOOR_H + 0.08)),
                     ((X1 - 0.02, DOOR_Y1, Z), (X1, DOOR_Y1 + 0.08, Z + DOOR_H + 0.08)),
                     ((X1 - 0.02, DOOR_Y0, Z + DOOR_H), (X1, DOOR_Y1, Z + DOOR_H + 0.08))):
        abox(p, mn, mx, at, WH)
    abox(b, (X1 - 0.86, Y0 + 0.02, Z + 0.01), (X1 - 0.06, Y0 + 0.06, Z + 2.0), at, WH, faces={'+Y': (at, RC("door"))})
    cylr(p, (X1 - 0.79, Y0 + 0.06, Z + 0.95), (X1 - 0.79, Y0 + 0.12, Z + 0.95), 0.012, 0.012, at, BL, segs=4)

    # --- люстра: три плафона ---
    cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
    # цилиндры строим снизу вверх: иначе грани смотрят внутрь
    cylr(p, (cx, cy, ZT - 0.2), (cx, cy, ZT), 0.008, 0.008, at, RC("brass"), segs=4)
    cylr(p, (cx, cy, ZT - 0.26), (cx, cy, ZT - 0.19), 0.02, 0.05, at, RC("brass"), segs=6)
    for k in range(3):
        a = math.radians(90 + k * 120)
        ex, ey = cx + math.cos(a) * 0.22, cy + math.sin(a) * 0.22
        cylr(p, (cx, cy, ZT - 0.22), (ex, ey, ZT - 0.18), 0.008, 0.008, at, RC("brass"), segs=4, caps=False)
        cylr(p, (ex, ey, ZT - 0.30), (ex, ey, ZT - 0.17), 0.03, 0.085, M["glass"], (0, 0, 1, 1), segs=8)   # плафон-тюльпан

    # --- комод под скатертью (как на фото): в углу у окна, от южной стены до левого края окна,
    #     4 ящика (нижний выдвинут), белая скатерть свисает спереди почти до пола, слева видны ящики ---
    cx0, cx1, cy0, cy1, ch = X0 + 0.07, X0 + 0.52, Y0 + 0.03, Y0 + 0.88, Z + 0.82          # отступ — за ним стояк
    abox(b, (cx0, cy0, Z), (cx1, cy1, ch), at, RC("wood"), faces={'+X': (at, RC("drawer"))})
    dr_ = RC("drawer")
    abox(p, (cx1, cy0 + 0.03, Z + 0.03), (cx1 + 0.06, cy1 - 0.03, Z + 0.19), at, RC("wood"),        # нижний ящик выдвинут
         faces={'+X': (at, (dr_[0], dr_[1], dr_[2], dr_[1] + (dr_[3] - dr_[1]) * 0.24))})
    fx = cx1 + 0.075                                                                               # скатерть спереди
    abox(p, (cx0 - 0.01, cy0, ch), (fx + 0.01, cy1 + 0.03, ch + 0.012), at, RC("cloth"))            # на крышке
    abox(p, (fx, cy0 + 0.24, Z + 0.10), (fx + 0.012, cy1 + 0.03, ch), at, RC("cloth"), skip=('-X',))   # свисает спереди
    abox(p, (cx0, cy1 + 0.015, Z + 0.30), (fx + 0.01, cy1 + 0.03, ch), at, RC("cloth"), skip=('-Y',))  # и сбоку
    t = ch + 0.012
    plant(p, (cx0 + 0.15, cy0 + 0.16, t), 13, 0.40, M, rng, spread=60)                              # большой спатифиллум
    obox(p, (cx0 + 0.34, cy0 + 0.17, t + 0.02), (0.20, 0.26, 0.035), at, RC("wood"),                # рамка лежит на краю
         faces={'+Z': (at, RC("picture"))}, yaw=4)
    abox(p, (cx0 + 0.10, cy0 + 0.32, t), (cx0 + 0.26, cy0 + 0.46, t + 0.11), at, BL)                 # чёрные коробочки
    abox(p, (cx0 + 0.28, cy0 + 0.36, t), (cx0 + 0.40, cy0 + 0.48, t + 0.06), at, BL)
    obox(p, (cx0 + 0.18, cy0 + 0.58, t + 0.03), (0.18, 0.24, 0.06), at, RC("book"), yaw=12)         # стопка книг
    obox(p, (cx0 + 0.18, cy0 + 0.57, t + 0.075), (0.16, 0.22, 0.04), at, RC("book"), yaw=-8)
    obox(p, (cx0 + 0.19, cy0 + 0.58, t + 0.11), (0.15, 0.20, 0.03), at, RC("book"), yaw=20)
    abox(p, (cx0 + 0.08, cy0 + 0.70, t), (cx0 + 0.18, cy0 + 0.80, t + 0.07), at, WH)                 # зарядка/роутер
    obox(p, (cx0 + 0.34, cy0 + 0.62, t + 0.005), (0.07, 0.14, 0.01), at, BL, yaw=20)                # телефон
    for k_ in range(4):                                                                              # провода
        cylr(p, (cx0 + 0.13, cy0 + 0.70, t + 0.01), (cx0 + 0.25 + k_ * 0.04, cy0 + 0.40 + k_ * 0.06, t + 0.004),
             0.004, 0.004, at, BL, segs=3, caps=False)

    # --- подоконник: цветок в оранжевом горшке, бутылка, ручка ---
    plant(p, (X0 + 0.06, 1.95, WZ0), 7, 0.28, M, rng, spread=45)
    cylr(p, (X0 + 0.08, 2.14, WZ0), (X0 + 0.08, 2.14, WZ0 + 0.26), 0.04, 0.04, at, RC("bottle"), segs=8)
    cylr(p, (X0 + 0.08, 2.14, WZ0 + 0.26), (X0 + 0.08, 2.14, WZ0 + 0.31), 0.04, 0.014, at, RC("bottle"), segs=8, caps=False)
    cylr(p, (X0 + 0.08, 2.14, WZ0 + 0.31), (X0 + 0.08, 2.14, WZ0 + 0.33), 0.015, 0.015, at, RC("cap"), segs=6)
    obox(p, (X0 + 0.15, 2.75, WZ0 + 0.005), (0.012, 0.14, 0.01), at, RC("cap"), yaw=-25)

    # --- кресло с одеждой (как на фото): во весь угол — от стены с окном до подлокотника дивана,
    #     спинкой к стене с панелями; округлая спинка, тёмная обивка в цветах, гора одежды сползает к батарее ---
    fab = M["fabric"]
    af = M["armchair"]
    sx0_ = X0 + 1.2                                             # где начинается диван (см. ниже)
    ax0, ax1, ay0, ay1 = X0 + 0.02, sx0_ - 0.05, Y1 - 0.86, Y1 - 0.04
    AW = ax1 - ax0
    AS = (0.5, 0.5)
    b.box((ax0 + 0.15, ay0, Z), (ax1 - 0.15, ay1 - 0.2, Z + 0.44), {k: af for k in ('+X', '-X', '+Z', '-Y')}, scale=AS)
    b.box((ax0, ay1 - 0.24, Z), (ax1, ay1, Z + 0.80), {k: af for k in ('+X', '-X', '-Y')}, scale=AS)          # спинка
    cylr(b, (ax0, ay1 - 0.13, Z + 0.80), (ax1, ay1 - 0.13, Z + 0.80), 0.13, 0.13, af, (0, 0, 1, 0.5), segs=8)  # её округлый верх
    for (xa, xb) in ((ax0, ax0 + 0.16), (ax1 - 0.16, ax1)):                                                  # подлокотники
        b.box((xa, ay0 + 0.04, Z), (xb, ay1 - 0.2, Z + 0.56), {k: af for k in ('+X', '-X', '-Y')}, scale=AS)
        cylr(b, ((xa + xb) / 2, ay0 + 0.04, Z + 0.56), ((xa + xb) / 2, ay1 - 0.2, Z + 0.56), 0.08, 0.08, af, (0, 0, 1, 0.5), segs=6)
    cl = RC("clothes")
    # (от спинки, доля ширины кресла, высота, размер x, y, z, поворот, наклон) — куча выше подлокотников, ниже спинки
    for (dx, fy, dz, sx, sy, sz, yw, pt) in (
            (0.55, 0.45, 0.52, 0.52, 0.62, 0.18, 8, 0), (0.48, 0.55, 0.66, 0.42, 0.48, 0.16, -14, 0),
            (0.56, 0.35, 0.74, 0.30, 0.36, 0.12, 25, 6), (0.62, 0.75, 0.60, 0.30, 0.30, 0.20, 40, 0),
            (0.60, 0.18, 0.62, 0.30, 0.26, 0.20, 10, 0), (0.42, 0.68, 0.76, 0.26, 0.30, 0.12, -30, 0),
            (0.74, 0.45, 0.40, 0.50, 0.40, 0.34, -6, -25),                                                    # сползает с сиденья
            (0.70, 0.10, 0.34, 0.40, 0.22, 0.46, 15, -18)):                                                   # свесилось к батарее
        obox(b, (ax0 + fy * AW, ay1 - dx, Z + dz), (sy, sx, sz), at, cl, yaw=yw, pitch=pt)
    obox(p, (ax0 + 0.16, ay0 - 0.06, Z + 0.28), (0.28, 0.05, 0.52), at, cl, yaw=8, pitch=-14)      # джинсы свесились на пол
    obox(p, (ax0 + 0.62 * AW, ay0 - 0.04, Z + 0.30), (0.10, 0.03, 0.42), at, WH, yaw=-4, pitch=-8)  # белое полотенце
    obox(b, (ax0 + 0.55 * AW, ay0 - 0.30, Z + 0.20), (0.50, 0.08, 0.40), at, BL, yaw=-8, pitch=-28)   # чёрная коробка у кресла
    obox(p, (ax0 + 0.22, ay0 - 0.22, Z + 0.06), (0.36, 0.28, 0.12), at, cl, yaw=20)               # куча на полу
    cylr(p, (ax0 + 0.50 * AW, ay0 - 0.12, Z + 0.62), (ax0 + 0.66 * AW, ay0 - 0.02, Z + 0.58), 0.04, 0.04, at, RC("bottle"), segs=8)   # бутылка в куче
    for k_ in range(2):                                                                            # провода из-под коробки
        cylr(p, (ax0 + 0.5 * AW + k_ * 0.08, ay0 - 0.36, Z + 0.01), (ax0 + 0.5 * AW + 0.22 + k_ * 0.05, ay0 - 0.70, Z + 0.01), 0.005, 0.005, at, BL, segs=3, caps=False)
    for (y_, yw) in ((2.78, 75), (2.56, 95)):                                                      # кроссовки у батареи
        obox(p, (X0 + 0.30, y_, Z + 0.05), (0.11, 0.28, 0.10), at, WH, yaw=yw)
        obox(p, (X0 + 0.30, y_, Z + 0.012), (0.12, 0.29, 0.024), at, BL, yaw=yw)

    # --- диван-кровать вдоль северной стены, разложен ---
    sx0, sx1 = X0 + 1.2, -7.58                                                 # вплотную к креслу; между комодом и кроватью — проход к окну
    sy1 = Y1 - 0.02
    bl = M["blanket"]
    b.box((sx0, 2.0, Z), (sx1, sy1, Z + 0.32), {k: fab for k in ('+X', '-X', '-Y')}, scale=(0.6, 0.6))
    b.box((sx0, sy1 - 0.26, Z + 0.32), (sx1, sy1, Z + 0.86), {k: fab for k in ('+X', '-X', '+Z', '-Y')}, scale=(0.6, 0.6))
    for (xa, xb) in ((sx0 - 0.04, sx0 + 0.2), (sx1 - 0.2, sx1 + 0.04)):                     # подлокотники
        b.box((xa, sy1 - 0.95, Z), (xb, sy1, Z + 0.66), {k: fab for k in ('+X', '-X', '+Z', '-Y')}, scale=(0.6, 0.6))
        cylr(b, (xa, sy1 - 0.95, Z + 0.66), (xb, sy1 - 0.95, Z + 0.66), 0.1, 0.1, fab, (0, 0, 1, 0.3), segs=6)
    # разложенная часть выдвинута далеко от стены (как на фото): шириной с диван, плед чуть свисает по бокам;
    # до стены с мангой остаётся проход ~0.7 м
    by0, by1 = Y0 + 0.70, sy1 - 0.95                                           # by1 — перед подлокотниками
    b.box((sx0, by0 + 0.04, Z), (sx1, by1, Z + 0.30), {k: fab for k in ('+X', '-X', '-Y')}, scale=(0.6, 0.6))
    abox(p, (sx0 + 0.03, by0 + 0.06, Z + 0.30), (sx1 - 0.03, by1, Z + 0.40), at, WH)            # простыня
    abox(p, (sx0 + 0.05, by1, Z + 0.32), (sx1 - 0.05, sy1 - 0.26, Z + 0.40), at, WH)
    b.box((sx0 - 0.05, by0, Z + 0.18), (sx1 + 0.05, by1, Z + 0.46),
          {'+Z': (bl, (0, 0, 1, 0.62)), '-Y': (bl, (0, 0, 1, 0.12)), '+X': (bl, (0.88, 0, 1, 0.62)), '-X': (bl, (0, 0, 0.12, 0.62))})
    b.box((sx0 + 0.02, by1, Z + 0.22), (sx1 - 0.02, sy1 - 0.27, Z + 0.46),
          {'+Z': (bl, (0, 0.62, 1, 1)), '+X': (bl, (0.88, 0.62, 1, 1)), '-X': (bl, (0, 0.62, 0.12, 1))})
    obox(p, (sx0 + 0.75, by0 + 0.75, Z + 0.50), (0.62, 0.5, 0.1), bl, (0.3, 0.3, 0.75, 0.7), yaw=-12,
         faces={'-Z': (bl, (0.3, 0.3, 0.75, 0.7))})                                            # сбившийся ком пледа
    obox(p, (sx0 + 0.5, sy1 - 0.45, Z + 0.52), (0.36, 0.26, 0.11), at, RC("pillow"), yaw=10)   # подушка

    # --- компьютерный стол в северо-восточном углу ---
    dx0, dx1, dy0, dy1 = -7.48, X1 - 0.02, Y1 - 0.64, Y1 - 0.02
    dt = Z + 0.74
    abox(b, (dx0, dy0, dt - 0.03), (dx1, dy1, dt), at, BL)
    for (x, y) in ((dx0 + 0.03, dy0 + 0.03), (dx1 - 0.03, dy0 + 0.03), (dx0 + 0.03, dy1 - 0.03), (dx1 - 0.03, dy1 - 0.03)):
        abox(b, (x - 0.025, y - 0.025, Z), (x + 0.025, y + 0.025, dt - 0.03), at, BL)
    abox(b, (dx0 + 0.03, dy1 - 0.05, Z + 0.12), (dx1 - 0.03, dy1 - 0.03, Z + 0.5), at, BL)     # задняя стенка
    abox(p, (dx0 + 0.04, dy0 + 0.02, dt), (dx0 + 0.82, dy0 + 0.34, dt + 0.003), at, RC("mousepad"))
    mx = -7.02
    # монитор 19" 5:4 на подставке
    abox(p, (mx - 0.12, dy1 - 0.30, dt), (mx + 0.12, dy1 - 0.12, dt + 0.015), at, BL)
    abox(p, (mx - 0.03, dy1 - 0.20, dt + 0.015), (mx + 0.03, dy1 - 0.16, dt + 0.17), at, BL)
    abox(b, (mx - 0.215, dy1 - 0.23, dt + 0.11), (mx + 0.215, dy1 - 0.17, dt + 0.47), at, BL)
    abox(p, (mx - 0.12, dy1 - 0.17, dt + 0.17), (mx + 0.12, dy1 - 0.10, dt + 0.40), at, BL)
    scr.box((mx - 0.19, dy1 - 0.232, dt + 0.135), (mx + 0.19, dy1 - 0.231, dt + 0.445), {'-Y': (M["screen"], (0, 0, 1, 1))})
    # системный блок на столе, справа от монитора
    abox(b, (dx1 - 0.215, dy0 + 0.08, dt), (dx1 - 0.025, dy0 + 0.55, dt + 0.43), at, RC("tower_s"),
         faces={'-Y': (at, RC("tower_f")), '+Z': (at, BL), '+Y': (at, BL)})
    # колонки 2.0
    for x in (mx - 0.40, dx1 - 0.33):
        abox(p, (x - 0.05, dy1 - 0.22, dt), (x + 0.05, dy1 - 0.13, dt + 0.18), at, BL, faces={'-Y': (at, RC("speaker"))})
    # клавиатура, мышь, кружка, бутылки
    abox(p, (mx - 0.23, dy0 + 0.06, dt + 0.003), (mx + 0.23, dy0 + 0.22, dt + 0.025), at, BL, faces={'+Z': (at, RC("keyb"))})
    obox(p, (mx + 0.33, dy0 + 0.14, dt + 0.018), (0.062, 0.11, 0.03), at, BL, yaw=-8)
    cylr(p, (mx + 0.33, dy0 + 0.19, dt + 0.03), (mx + 0.25, dy0 + 0.40, dt + 0.003), 0.003, 0.003, at, BL, segs=3, caps=False)
    cylr(p, (dx0 + 0.12, dy0 + 0.26, dt), (dx0 + 0.12, dy0 + 0.26, dt + 0.10), 0.042, 0.042, at, RC("mug"), segs=8)
    for (x, y, hh) in ((dx0 + 0.13, dy1 - 0.14, 0.30), (dx0 + 0.26, dy1 - 0.10, 0.24)):
        cylr(p, (x, y, dt), (x, y, dt + hh), 0.045, 0.045, at, RC("bottle"), segs=8)
        cylr(p, (x, y, dt + hh), (x, y, dt + hh + 0.06), 0.045, 0.015, at, RC("bottle"), segs=8, caps=False)
        cylr(p, (x, y, dt + hh + 0.06), (x, y, dt + hh + 0.08), 0.016, 0.016, at, RC("cap"), segs=6)
    # миска с ложкой и красная мягкая игрушка на системнике (как на фото стены)
    bx_, by_ = dx0 + 0.17, dy0 + 0.09
    cylr(p, (bx_, by_, dt), (bx_, by_, dt + 0.055), 0.035, 0.07, at, WH, segs=8)
    cylr(p, (bx_, by_, dt + 0.05), (bx_, by_, dt + 0.052), 0.058, 0.058, at, RC("soil"), segs=8)
    obox(p, (bx_ + 0.05, by_ + 0.04, dt + 0.07), (0.012, 0.17, 0.005), at, WH, yaw=-55, pitch=18)
    cylr(p, (dx1 - 0.12, dy0 + 0.33, dt + 0.43), (dx1 - 0.12, dy0 + 0.33, dt + 0.54), 0.07, 0.06, at, RC("plush"), segs=8)
    # провода из-под стола: вниз за столом, по полу вдоль стены к розетке под выключателем
    for k in range(3):
        y_, zz = 2.24 - k * 0.012, Z + 0.33 + k * 0.012
        pts_ = [(dx1 - 0.1 - k * 0.05, dy1 - 0.08, dt), (X1 - 0.03 - k * 0.01, Y1 - 0.3, Z + 0.015),
                (X1 - 0.03 - k * 0.01, y_ + 0.06, Z + 0.015), (X1 - 0.015, y_, zz)]
        for a_, b_ in zip(pts_, pts_[1:]):
            cylr(p, a_, b_, 0.004, 0.004, at, BL, segs=3, caps=False)

    # гирлянда с зелёными бусинами вдоль восточной стены, над надписями (провисает между гвоздиками)
    pins = [(3.85, ZT - 0.30), (3.48, ZT - 0.28), (3.12, ZT - 0.25), (2.76, ZT - 0.22), (2.40, ZT - 0.19)]
    gx = X1 - 0.012
    wire = []
    for (ya, za), (yb, zb) in zip(pins, pins[1:]):
        for t in np.linspace(0, 1, 6)[:-1]:
            wire.append((ya + (yb - ya) * t, za + (zb - za) * t - 0.035 * 4 * t * (1 - t)))
    wire.append(pins[-1])
    for (ya, za), (yb, zb) in zip(wire, wire[1:]):
        cylr(p, (gx, ya, za), (gx, yb, zb), 0.002, 0.002, at, BL, segs=3, caps=False)
    for i, (y_, z_) in enumerate(wire[1:-1]):
        if i % 2 == 0:
            obox(p, (gx - 0.004, y_, z_ - 0.008), (0.016, 0.016, 0.016), at, RC("bead"), yaw=30 * i)

    # надписи маркером — прозрачная наклейка в 4 мм от стены
    wr = B()
    wr.box((X1 - 0.005, WR_Y0, Z + WR_Z0), (X1 - 0.004, WR_Y1, Z + WR_Z1), {'-X': (M["writing"], (0, 0, 1, 1))})

    # --- игровое кресло (зелёно-чёрное), развёрнуто к столу ---
    chx, chy, cyaw = mx + 0.05, Y1 - 1.18, 12.0
    rot = Euler((0, 0, math.radians(cyaw)), 'XYZ').to_matrix()
    P = lambda lx, ly, lz: tuple(Vector((chx, chy, Z)) + rot @ Vector((lx, ly, lz)))
    G, K = RC("chair_g"), RC("chair_b")
    for k in range(5):
        a = k * 72 + cyaw
        r = math.radians(a)
        obox(b, (chx + math.cos(r) * 0.16, chy + math.sin(r) * 0.16, Z + 0.07), (0.32, 0.05, 0.04), at, BL, yaw=a)
        abox(p, (chx + math.cos(r) * 0.31 - 0.025, chy + math.sin(r) * 0.31 - 0.025, Z), (chx + math.cos(r) * 0.31 + 0.025, chy + math.sin(r) * 0.31 + 0.025, Z + 0.05), at, BL)
    cylr(b, (chx, chy, Z + 0.07), (chx, chy, Z + 0.42), 0.03, 0.03, at, BL, segs=6)
    obox(b, P(0, 0, 0.47), (0.52, 0.52, 0.09), at, K, yaw=cyaw)
    for sx in (-0.23, 0.23):
        obox(b, P(sx, 0, 0.51), (0.08, 0.52, 0.08), at, G, yaw=cyaw)
    obox(b, P(0, -0.29, 0.96), (0.36, 0.09, 0.88), at, K, yaw=cyaw, pitch=-10)            # спинка: чёрная середина
    for sx in (-0.21, 0.21):                                                               # зелёные боковины
        obox(b, P(sx, -0.28, 0.96), (0.10, 0.12, 0.86), at, G, yaw=cyaw, pitch=-10)
    obox(p, P(0, -0.20, 1.22), (0.24, 0.07, 0.12), at, K, yaw=cyaw, pitch=-10)               # подушка под шею
    obox(p, P(0, -0.22, 0.72), (0.26, 0.08, 0.12), at, K, yaw=cyaw, pitch=-10)               # поясничная подушка
    for sx in (-0.31, 0.31):
        obox(p, P(sx, 0.02, 0.66), (0.06, 0.28, 0.035), at, BL, yaw=cyaw)
        obox(p, P(sx, -0.05, 0.58), (0.035, 0.035, 0.16), at, BL, yaw=cyaw)

    main = b.build("YurRoom", coll)
    props = p.build("YurRoomProps_nocol", coll)
    screen = scr.build("PCScreen_nocol", coll)
    writing = wr.build("EastWriting_nocol", coll)
    export("yurchik_room", [main, props, screen, writing])
    return {"room_polys": len(main.data.polygons), "props_polys": len(props.data.polygons)}


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
    tex_panels(); tex_west(); tex_south(); tex_east(); tex_floor_ceiling()
    tex_blanket(); tex_fabric(); tex_window(); tex_screen(); tex_atlas()
    render_writing()
    M = {
        "panels": mat("YrPanels", "yr_panels"), "west": mat("YrWest", "yr_west"), "south": mat("YrSouth", "yr_south"),
        "east": mat("YrEast", "yr_east"), "floor": mat("YrLaminate", "yr_laminate", rough=0.5),
        "ceiling": mat("YrCeiling", "yr_ceiling"), "blanket": mat("YrBlanket", "yr_blanket"),
        "fabric": mat("YrFabric", "yr_fabric"), "armchair": mat("YrArmchair", "yr_armchair"), "window": mat("YrWindow", "yr_window", "yr_window_emission", rough=0.3),
        "screen": mat("YrScreen", "yr_screen", "yr_screen_emission", rough=0.2), "atlas": mat("YrAtlas", "yr_atlas", rough=0.7),
        "radiator": mat("YrRadiator", "radiator", rough=0.6), "radiator_m": mat("YrPipe", "radiator", rough=0.6),
        "glass": mat("YrLampGlass", "lamp_glass", "lamp_glass", rough=0.3),
        "writing": mat_alpha("YrWriting", "yr_writing"),
    }
    print("BUILD_YUR_ROOM " + str(room(M)))


main()
