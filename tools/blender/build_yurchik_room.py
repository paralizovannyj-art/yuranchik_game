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
#   * белая стена с дверью: красные каракули маркером над столом, выключатель, розетка;
#     на стене напротив дивана — обрывки старых газетных обоев у двери; люстра с тремя плафонами, светлый ламинат.
#
# Запуск (Blender 5.2, из корня проекта):
#   blender -b --factory-startup --python tools/blender/build_yurchik_room.py
# Результат: assets/textures/yr_*.png, assets/models/yurchik_room.gltf
#
# Координаты — те же, что у подъезда (build_mvp_assets.py): комната на 4-м этаже, x −10.2…−6.32, y −0.6…3.6,
# пол на z = 8.4. Поэтому модель ставится в stairwell.tscn без смещения.
# Объекты: YurRoom — стены и мебель (с коллизией), YurRoomProps_nocol — мелочь, PCScreen_nocol — экран монитора
# (отдельно, чтобы игра могла его «включить»).
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
X0, X1, XF = -10.2, -6.32, -6.2        # западная стена (окно), восточная стена (дверь), край пола под проёмом
Y0, Y1 = -0.6, 3.6                     # южная стена (обрывки обоев), северная (диван, панели)
Z, H = 8.4, 2.5
ZT = Z + H
DOOR_Y0, DOOR_Y1, DOOR_H = 0.6, 1.9, 2.05


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


def _sheet(arr, x0, y0, w, h, rng):
    """Обрывок газетных обоев с рваным краем и тенью."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    edge = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
    rag = noise(w, h, max(2, w // 4), max(2, h // 4), rng, oct=2) * 5
    m = (edge + 1.5 > rag).astype(np.float32)
    paper = C(0.66, 0.63, 0.55) * (0.85 + 0.25 * noise(w, h, 4, 4, rng, oct=3))[..., None]
    paper *= np.where((yy % 3 < 1)[..., None] & ((xx % 14) < 11)[..., None], 0.55, 1.0)   # строки текста
    paper[:, w // 2 - 1:w // 2] *= 0.85                                                 # колонки
    if w > 30 and h > 18:
        paper[3:12, 3:16] = C(0.30, 0.29, 0.27)                                          # фотография
    paper *= np.linspace(1.0, 0.8, h, dtype=np.float32)[:, None, None]                   # пожелтело к низу
    reg = arr[y0:y0 + h, x0:x0 + w]
    reg[:] = reg * (1 - m[..., None]) + paper * m[..., None]
    arr[y0 + h:y0 + h + 2, x0 + 2:x0 + w + 2] *= 0.75                                    # тень


def tex_south():
    """Стена напротив дивана: побелка, у двери полоса из обрывков газетных обоев, красные каракули."""
    w, h = 512, 256
    arr = plaster(R, w, h, (0.74, 0.72, 0.66), streak=0.2, stains=0.35, crack=0.25)
    arr = peeled(arr, R, C(0.56, 0.54, 0.48), 16, 0.05)
    # слева (у двери, восточный край) — обрывки на высоте 0.7…2.3 м (1 px ≈ 1 см по высоте)
    y = 20
    while y < 180:
        sw, sh = int(R.integers(34, 62)), int(R.integers(18, 30))
        _sheet(arr, int(R.integers(6, 48)), y, sw, sh, R)
        y += int(sh * 0.75)
    for _ in range(5):
        scribble(arr, int(R.integers(80, 300)), int(R.integers(70, 150)), 10, C(0.55, 0.09, 0.07), R, step=3, width=1)
    arr *= (1 - floor_grime(h, w, R, 0.25, 0.45))[..., None]
    save("yr_south", finish(arr, 1.2))


def tex_east():
    """Стена с дверью: белая штукатурка, у потолка отвалилась; над столом красные надписи маркером,
    выключатель у двери, розетка под столом. Левый край текстуры — северный угол (стол)."""
    w, h = 512, 256
    arr = plaster(R, w, h, (0.78, 0.77, 0.72), streak=0.2, stains=0.3, crack=0.3)
    top = np.zeros((h, w), np.float32); top[:70] = 1
    top = blur(top[..., None], 8)[..., 0]
    patches = smoothstep(0.55, 0.62, noise(w, h, 10, 5, R, oct=3)) * top
    under = C(0.55, 0.53, 0.47) * (0.85 + 0.3 * noise(w, h, 16, 8, R))[..., None]
    arr = arr * (1 - patches[..., None]) + under * patches[..., None]
    rim = np.clip(patches - np.roll(patches, (2, 2), (0, 1)), 0, 1)
    arr *= (1 - rim * 0.5)[..., None]
    red = C(0.62, 0.10, 0.07)
    for line in range(7):                                       # «надписи» над столом: слова-каракули
        x = 18 + int(R.integers(0, 10)); yl = 66 + line * 12 + int(R.integers(-2, 3))
        while x < 150:
            scribble(arr, x, yl, int(R.integers(4, 9)), red, R, step=2, width=1)
            x += int(R.integers(14, 26))
    scribble(arr, 160, 90, 12, red, R, step=4, width=1)
    sx, sy = 183, 160                                            # выключатель у двери (y ≈ 2.1 м, h ≈ 0.95 м)
    arr[sy - 1:sy + 13, sx - 1:sx + 11] *= 0.6
    arr[sy:sy + 12, sx:sx + 10] = C(0.80, 0.78, 0.70)
    arr[sy + 2:sy + 10, sx + 3:sx + 7] = C(0.70, 0.68, 0.60)
    ox, oy = 43, 222                                             # розетка
    arr[oy - 1:oy + 11, ox - 1:ox + 11] *= 0.6
    arr[oy:oy + 10, ox:ox + 10] = C(0.78, 0.76, 0.68)
    arr[oy + 4:oy + 6, ox + 2:ox + 4] = C(0.1, 0.1, 0.1); arr[oy + 4:oy + 6, ox + 6:ox + 8] = C(0.1, 0.1, 0.1)
    arr *= (1 - floor_grime(h, w, R, 0.2, 0.4))[..., None]
    save("yr_east", finish(arr, 1.2))


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
    frame[60:72, 54:58] = True                                            # ручка
    white = C(0.80, 0.80, 0.76) * (0.85 + 0.2 * noise(s, s, 8, 8, R))[..., None]
    alb = np.where(frame[..., None], white, glass)
    alb[60:72, 54:58] = C(0.86, 0.86, 0.84)
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
    # комод: шпон, три ящика, латунные ручки
    wd = np.ones((64, 64, 3), np.float32) * C(0.38, 0.21, 0.11) * (0.75 + 0.5 * noise(64, 64, 2, 16, R, oct=3))[..., None]
    put("wood", wd.copy())
    for k in (0, 21, 42):
        wd[k:k + 2] *= 0.35
        wd[k + 9:k + 12, 26:38] = C(0.62, 0.50, 0.25)
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
    WY0, WY1, WZ0, WZ1 = 0.85, 2.15, Z + 0.88, Z + 2.2
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
    b.box((X0 + 0.04, 0.95, Z + 0.12), (X0 + 0.14, 2.05, Z + 0.72),
          {'+X': (M["radiator"], (0, 0, 2.2, 1)), '+Z': M["radiator"], '+Y': M["radiator"], '-Y': M["radiator"]}, scale=(0.3, 0.3))
    for z in (Z + 0.2, Z + 0.64):
        cylr(p, (X0 + 0.06, 0.62, z), (X0 + 0.06, 0.95, z), 0.016, 0.016, M["radiator_m"], (0, 0, 1, 1), segs=6, caps=False)
    cylr(p, (X0 + 0.06, 0.62, Z), (X0 + 0.06, 0.62, ZT), 0.022, 0.022, M["radiator_m"], (0, 0, 1, 1), segs=6, caps=False)

    # --- дверь: наличник и открытое полотно у стены ---
    for (mn, mx) in (((X1 - 0.02, DOOR_Y0 - 0.08, Z), (X1, DOOR_Y0, Z + DOOR_H + 0.08)),
                     ((X1 - 0.02, DOOR_Y1, Z), (X1, DOOR_Y1 + 0.08, Z + DOOR_H + 0.08)),
                     ((X1 - 0.02, DOOR_Y0, Z + DOOR_H), (X1, DOOR_Y1, Z + DOOR_H + 0.08))):
        abox(p, mn, mx, at, WH)
    abox(b, (X1 - 0.06, -0.22, Z + 0.01), (X1 - 0.02, DOOR_Y0 - 0.1, Z + 2.0), at, WH, faces={'-X': (at, RC("door"))})
    cylr(p, (X1 - 0.06, -0.18, Z + 0.95), (X1 - 0.12, -0.18, Z + 0.95), 0.012, 0.012, at, BL, segs=4)

    # --- люстра: три плафона ---
    cx, cy = (X0 + X1) / 2, 1.5
    # цилиндры строим снизу вверх: иначе грани смотрят внутрь
    cylr(p, (cx, cy, ZT - 0.2), (cx, cy, ZT), 0.008, 0.008, at, RC("brass"), segs=4)
    cylr(p, (cx, cy, ZT - 0.26), (cx, cy, ZT - 0.19), 0.02, 0.05, at, RC("brass"), segs=6)
    for k in range(3):
        a = math.radians(90 + k * 120)
        ex, ey = cx + math.cos(a) * 0.22, cy + math.sin(a) * 0.22
        cylr(p, (cx, cy, ZT - 0.22), (ex, ey, ZT - 0.18), 0.008, 0.008, at, RC("brass"), segs=4, caps=False)
        cylr(p, (ex, ey, ZT - 0.30), (ex, ey, ZT - 0.17), 0.03, 0.085, M["glass"], (0, 0, 1, 1), segs=8)   # плафон-тюльпан

    # --- комод под скатертью (юго-западный угол) ---
    cx0, cx1, cy0, cy1, ch = X0 + 0.02, X0 + 0.52, Y0 + 0.03, Y0 + 0.85, Z + 0.78
    abox(b, (cx0, cy0, Z), (cx1, cy1, ch), at, RC("wood"), faces={'+X': (at, RC("drawer"))})
    abox(p, (cx0 - 0.01, cy0, ch), (cx1 + 0.06, cy1 + 0.03, ch + 0.012), at, RC("cloth"))
    abox(p, (cx1 + 0.05, cy0, Z + 0.40), (cx1 + 0.065, cy1 + 0.03, ch), at, RC("cloth"), skip=('-X',))
    abox(p, (cx0, cy1 + 0.015, Z + 0.52), (cx1 + 0.06, cy1 + 0.03, ch), at, RC("cloth"), skip=('-Y',))
    t = ch + 0.012
    plant(p, (cx0 + 0.16, cy0 + 0.17, t), 11, 0.36, M, rng, spread=55)
    obox(p, (cx0 + 0.06, cy0 + 0.47, t + 0.15), (0.02, 0.24, 0.30), at, RC("picture"), pitch=0, yaw=0,
         faces={'+X': (at, RC("picture"))})                                                 # икона в рамке
    abox(p, (cx0 + 0.18, cy0 + 0.38, t), (cx0 + 0.34, cy0 + 0.60, t + 0.12), at, BL)        # коробки
    abox(p, (cx0 + 0.20, cy0 + 0.58, t), (cx0 + 0.30, cy0 + 0.70, t + 0.05), at, BL)
    obox(p, (cx0 + 0.36, cy0 + 0.74, t + 0.03), (0.16, 0.22, 0.06), at, RC("book"), yaw=12)  # книги
    obox(p, (cx0 + 0.36, cy0 + 0.73, t + 0.075), (0.14, 0.2, 0.03), at, RC("book"), yaw=-8)
    obox(p, (cx0 + 0.40, cy0 + 0.45, t + 0.005), (0.07, 0.14, 0.01), at, BL, yaw=20)        # телефон

    # --- подоконник: цветок в оранжевом горшке, бутылка, ручка ---
    plant(p, (X0 + 0.06, 1.1, WZ0), 7, 0.28, M, rng, spread=45)
    cylr(p, (X0 + 0.08, 1.45, WZ0), (X0 + 0.08, 1.45, WZ0 + 0.26), 0.04, 0.04, at, RC("bottle"), segs=8)
    cylr(p, (X0 + 0.08, 1.45, WZ0 + 0.26), (X0 + 0.08, 1.45, WZ0 + 0.31), 0.04, 0.014, at, RC("bottle"), segs=8, caps=False)
    cylr(p, (X0 + 0.08, 1.45, WZ0 + 0.31), (X0 + 0.08, 1.45, WZ0 + 0.33), 0.015, 0.015, at, RC("cap"), segs=6)
    obox(p, (X0 + 0.15, 1.85, WZ0 + 0.005), (0.012, 0.14, 0.01), at, RC("cap"), yaw=-25)

    # --- кресло с одеждой (северо-западный угол) ---
    fab = M["fabric"]
    ax0, ax1, ay0, ay1 = X0 + 0.04, X0 + 0.84, Y1 - 0.86, Y1 - 0.04
    b.box((ax0 + 0.2, ay0 + 0.16, Z), (ax1, ay1 - 0.16, Z + 0.42), {k: fab for k in ('+X', '+Z', '-Y', '+Y')}, scale=(0.6, 0.6))
    b.box((ax0, ay0, Z), (ax0 + 0.22, ay1, Z + 0.88), {k: fab for k in ('+X', '+Z', '-Y', '+Y')}, scale=(0.6, 0.6))
    for (ya, yb) in ((ay0, ay0 + 0.17), (ay1 - 0.17, ay1)):
        b.box((ax0 + 0.2, ya, Z), (ax1, yb, Z + 0.62), {k: fab for k in ('+X', '-X', '+Z', '-Y', '+Y')}, scale=(0.6, 0.6))
    cl = RC("clothes")
    for (dx, dy, dz, sx, sy, sz, yw) in ((0.45, 0.35, 0.50, 0.50, 0.46, 0.18, 8), (0.40, 0.45, 0.66, 0.42, 0.40, 0.16, -14),
                                         (0.50, 0.30, 0.80, 0.34, 0.30, 0.14, 25), (0.30, 0.55, 0.88, 0.30, 0.34, 0.12, -30),
                                         (0.62, 0.62, 0.58, 0.30, 0.28, 0.22, 40), (0.55, 0.10, 0.62, 0.28, 0.20, 0.2, 10)):
        obox(b, (ax0 + dx, ay0 + dy, Z + dz), (sx, sy, sz), at, cl, yaw=yw)
    obox(p, (ax1 + 0.12, ay0 + 0.2, Z + 0.3), (0.06, 0.3, 0.6), at, cl, yaw=5, pitch=12)       # свесилось на пол
    obox(b, (X0 + 0.45, 2.25, Z + 0.17), (0.42, 0.28, 0.34), at, BL, yaw=-10)                  # чёрная сумка у батареи

    # --- диван-кровать вдоль северной стены, разложен ---
    sx0, sx1 = X0 + 0.9, -7.58
    sy1 = Y1 - 0.02
    bl = M["blanket"]
    b.box((sx0, 2.0, Z), (sx1, sy1, Z + 0.32), {k: fab for k in ('+X', '-X', '-Y')}, scale=(0.6, 0.6))
    b.box((sx0, sy1 - 0.26, Z + 0.32), (sx1, sy1, Z + 0.86), {k: fab for k in ('+X', '-X', '+Z', '-Y')}, scale=(0.6, 0.6))
    for (xa, xb) in ((sx0 - 0.04, sx0 + 0.2), (sx1 - 0.2, sx1 + 0.04)):                     # подлокотники
        b.box((xa, sy1 - 0.95, Z), (xb, sy1, Z + 0.66), {k: fab for k in ('+X', '-X', '+Z', '-Y')}, scale=(0.6, 0.6))
        cylr(b, (xa, sy1 - 0.95, Z + 0.66), (xb, sy1 - 0.95, Z + 0.66), 0.1, 0.1, fab, (0, 0, 1, 0.3), segs=6)
    abox(p, (sx0 + 0.05, 2.02, Z + 0.32), (sx1 - 0.05, sy1 - 0.26, Z + 0.40), at, WH)          # простыня
    b.box((sx0 + 0.02, 1.96, Z + 0.22), (sx1 - 0.02, sy1 - 0.27, Z + 0.46),
          {'+Z': (bl, (0, 0, 1, 1)), '-Y': (bl, (0, 0, 1, 0.12)), '+X': (bl, (0.88, 0, 1, 1)), '-X': (bl, (0, 0, 0.12, 1))})
    obox(p, (sx0 + 0.75, 2.55, Z + 0.50), (0.62, 0.5, 0.1), bl, (0.3, 0.3, 0.75, 0.7), yaw=-12,
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
    # провода из-под стола к розетке
    for k in range(3):
        cylr(p, (dx1 - 0.1 - k * 0.05, dy1 - 0.08, dt), (X1 - 0.02, 3.25 - k * 0.03, Z + 0.32), 0.004, 0.004, at, BL, segs=3, caps=False)

    # --- игровое кресло (зелёно-чёрное), развёрнуто к столу ---
    chx, chy, cyaw = mx + 0.05, 2.42, 12.0
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
    export("yurchik_room", [main, props, screen])
    return {"room_polys": len(main.data.polygons), "props_polys": len(props.data.polygons)}


def main():
    for ob in list(bpy.context.scene.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    tex_panels(); tex_west(); tex_south(); tex_east(); tex_floor_ceiling()
    tex_blanket(); tex_fabric(); tex_window(); tex_screen(); tex_atlas()
    M = {
        "panels": mat("YrPanels", "yr_panels"), "west": mat("YrWest", "yr_west"), "south": mat("YrSouth", "yr_south"),
        "east": mat("YrEast", "yr_east"), "floor": mat("YrLaminate", "yr_laminate", rough=0.5),
        "ceiling": mat("YrCeiling", "yr_ceiling"), "blanket": mat("YrBlanket", "yr_blanket"),
        "fabric": mat("YrFabric", "yr_fabric"), "window": mat("YrWindow", "yr_window", "yr_window_emission", rough=0.3),
        "screen": mat("YrScreen", "yr_screen", "yr_screen_emission", rough=0.2), "atlas": mat("YrAtlas", "yr_atlas", rough=0.7),
        "radiator": mat("YrRadiator", "radiator", rough=0.6), "radiator_m": mat("YrPipe", "radiator", rough=0.6),
        "glass": mat("YrLampGlass", "lamp_glass", "lamp_glass", rough=0.3),
    }
    print("BUILD_YUR_ROOM " + str(room(M)))


main()
